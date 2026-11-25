# pylint: disable=missing-function-docstring,redefined-outer-name
"""Mocked tests for sandbox files (``pydo.sandbox``), through the real pipeline."""

import hashlib
import json
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import pytest
import responses

from pydo.sandbox import (
    FileEntry,
    InvalidRequestError,
    MakeDirResult,
    NotFoundError,
    Sandbox,
    SandboxError,
    ServiceError,
    WriteInfo,
)
from pydo.sandbox import _files
from pydo.sandbox import files as files_module

API = "https://sandbox.test"
CONN = {"token": "test-token", "api_url": API}
FILES = API + "/v2/sandboxes/sb-1/files"


def entry(**extra):
    out = {
        "name": "hello.txt",
        "type": "FILE_ENTRY_TYPE_FILE",
        "path": "/workspace/hello.txt",
        "size": "12",
        "mode": 420,
        "permissions": "-rw-r--r--",
        "owner": "user",
        "group": "user",
        "modified_time": "2026-03-25T12:00:00Z",
    }
    out.update(extra)
    return out


def footer(payload, digest=None):
    digest = digest or hashlib.sha256(payload).hexdigest()
    return payload + b"DOWSSHA1" + digest.encode("ascii") + b"\n"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("DIGITALOCEAN_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("DIGITALOCEAN_API_URL", raising=False)


@pytest.fixture
def rsps():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        yield mock


@pytest.fixture
def sleeps(monkeypatch):
    waited = []
    monkeypatch.setattr(files_module.time, "sleep", waited.append)
    return waited


@pytest.fixture
def sandbox(rsps):
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/sb-1",
        json={
            "sandbox": {
                "sandbox_id": "sb-1",
                "template": "coding-base",
                "state": "SANDBOX_STATE_RUNNING",
            }
        },
    )
    sb = Sandbox.get("sb-1", **CONN)
    rsps.calls.reset()
    yield sb
    sb.close()


def query(call):
    return {k: v[0] for k, v in parse_qs(urlparse(call.request.url).query).items()}


def body_of(call):
    return json.loads(call.request.body)


def test_write_text_sends_raw_bytes_and_their_sha256(rsps, sandbox):
    rsps.add(
        responses.POST,
        FILES + "/upload",
        json={"path": "/workspace/hello.txt", "bytes_written": "6"},
    )
    info = sandbox.files.write("/workspace/hello.txt", "héllo")
    assert info == WriteInfo(path="/workspace/hello.txt", bytes_written=6)
    request = rsps.calls[0].request
    assert request.body == "héllo".encode("utf-8")
    assert request.headers["Content-Type"] == "application/octet-stream"
    assert (
        request.headers["X-Content-Sha256"]
        == hashlib.sha256("héllo".encode("utf-8")).hexdigest()
    )
    assert request.headers["Authorization"] == "Bearer test-token"
    assert query(rsps.calls[0]) == {"path": "/workspace/hello.txt"}


def test_write_bytes_and_archive(rsps, sandbox):
    rsps.add(
        responses.POST,
        FILES + "/upload",
        json={"path": "/workspace/out", "bytes_written": "3"},
    )
    sandbox.files.write("/workspace/a.bin", b"\x00\xff\x10")
    assert rsps.calls[0].request.body == b"\x00\xff\x10"
    info = sandbox.files.write_archive("/workspace/out", b"tar")
    assert info.bytes_written == 3
    assert query(rsps.calls[1]) == {"path": "/workspace/out", "is_archive": "true"}
    assert (
        rsps.calls[1].request.headers["X-Content-Sha256"]
        == hashlib.sha256(b"tar").hexdigest()
    )


def test_read_strips_and_checks_the_footer(rsps, sandbox):
    rsps.add(
        responses.GET,
        FILES + "/download",
        body=footer(b"hello\n"),
        content_type="application/octet-stream",
        headers={"X-Workspace-Is-Archive": "false", "X-Workspace-Size-Bytes": "6"},
    )
    assert sandbox.files.read("/workspace/hello.txt") == b"hello\n"
    assert query(rsps.calls[0]) == {"path": "/workspace/hello.txt"}
    assert sandbox.files.read_text("/workspace/hello.txt") == "hello\n"


def test_read_an_empty_file(rsps, sandbox):
    rsps.add(
        responses.GET,
        FILES + "/download",
        body=footer(b""),
        content_type="application/octet-stream",
    )
    assert sandbox.files.read("/workspace/empty") == b""


def test_read_archive_asks_for_a_tar(rsps, sandbox):
    rsps.add(
        responses.GET,
        FILES + "/download",
        body=footer(b"tar-bytes"),
        content_type="application/octet-stream",
        headers={"X-Workspace-Is-Archive": "true"},
    )
    assert sandbox.files.read_archive("/workspace/dir") == b"tar-bytes"
    assert query(rsps.calls[0]) == {"path": "/workspace/dir", "as_archive": "true"}


def test_read_rejects_a_bad_or_missing_footer(rsps, sandbox):
    rsps.add(
        responses.GET,
        FILES + "/download",
        body=footer(b"hello", digest="0" * 64),
        content_type="application/octet-stream",
    )
    with pytest.raises(SandboxError, match="integrity check"):
        sandbox.files.read("/workspace/hello.txt")
    rsps.replace(
        responses.GET,
        FILES + "/download",
        body=b"hello",
        content_type="application/octet-stream",
    )
    with pytest.raises(SandboxError, match="footer"):
        sandbox.files.read("/workspace/hello.txt")


def test_split_download_validates_every_footer_part():
    digest = hashlib.sha256(b"x").hexdigest()
    assert _files.split_download(footer(b"x")) == b"x"
    for bad in (
        b"x" + b"DOWSSHA2" + digest.encode() + b"\n",
        b"x" + b"DOWSSHA1" + digest.upper().encode() + b"\n",
        b"x" + b"DOWSSHA1" + digest.encode() + b"\r",
        b"DOWSSHA1",
    ):
        with pytest.raises(SandboxError, match="footer"):
            _files.split_download(bad)


def test_download_error_is_typed(rsps, sandbox):
    rsps.add(
        responses.GET,
        FILES + "/download",
        json={"id": "not_found", "message": "no such file"},
        status=404,
    )
    with pytest.raises(NotFoundError, match="no such file"):
        sandbox.files.read("/workspace/missing")


def test_upload_503_is_retried_with_backoff(rsps, sandbox, sleeps):
    busy = {"id": "service_unavailable", "message": "Too many transfers"}
    rsps.add(responses.POST, FILES + "/upload", json=busy, status=503)
    rsps.add(responses.POST, FILES + "/upload", json=busy, status=503)
    rsps.add(
        responses.POST, FILES + "/upload", json={"path": "/a", "bytes_written": "1"}
    )
    assert sandbox.files.write("/a", "x").bytes_written == 1
    assert len(rsps.calls) == 3
    assert sleeps == [0.5, 1.0]
    assert rsps.calls[2].request.body == b"x"


def test_upload_503_gives_up_after_three_retries(rsps, sandbox, sleeps):
    rsps.add(
        responses.POST,
        FILES + "/upload",
        json={"id": "service_unavailable", "message": "Too many transfers"},
        status=503,
    )
    with pytest.raises(ServiceError, match="Too many transfers") as err:
        sandbox.files.write("/a", "x")
    assert err.value.status == 503
    assert len(rsps.calls) == 4
    assert sleeps == [0.5, 1.0, 2.0]


def test_download_503_honours_retry_after(rsps, sandbox, sleeps):
    rsps.add(
        responses.GET,
        FILES + "/download",
        json={"id": "service_unavailable", "message": "busy"},
        status=503,
        headers={"Retry-After": "3"},
    )
    rsps.add(
        responses.GET,
        FILES + "/download",
        body=footer(b"ok"),
        content_type="application/octet-stream",
    )
    assert sandbox.files.read("/a") == b"ok"
    assert sleeps == [3.0]


def test_other_errors_are_not_retried(rsps, sandbox, sleeps):
    rsps.add(
        responses.POST,
        FILES + "/upload",
        json={"id": "payload_too_large", "message": "too big"},
        status=413,
    )
    with pytest.raises(SandboxError, match="too big") as err:
        sandbox.files.write("/a", "x")
    assert err.value.status == 413
    assert len(rsps.calls) == 1
    assert not sleeps


def test_list_parses_entries(rsps, sandbox):
    rsps.add(
        responses.GET,
        FILES + "/list",
        json={
            "entries": [
                entry(),
                entry(
                    name="link",
                    path="/workspace/link",
                    type="FILE_ENTRY_TYPE_SYMLINK",
                    symlink_target="/workspace/hello.txt",
                    size="0",
                ),
                entry(name="d", path="/workspace/d", type="FILE_ENTRY_TYPE_DIRECTORY"),
                {"path": "/workspace/odd", "type": "FILE_ENTRY_TYPE_UNSPECIFIED"},
            ]
        },
    )
    entries = sandbox.files.list("/workspace", depth=2)
    assert query(rsps.calls[0]) == {"path": "/workspace", "depth": "2"}
    assert entries[0] == FileEntry(
        name="hello.txt",
        type="file",
        path="/workspace/hello.txt",
        size=12,
        mode=420,
        permissions="-rw-r--r--",
        owner="user",
        group="user",
        modified_time=datetime(2026, 3, 25, 12, tzinfo=timezone.utc),
        symlink_target=None,
    )
    assert (entries[1].type, entries[1].symlink_target) == (
        "symlink",
        "/workspace/hello.txt",
    )
    assert entries[2].type == "directory"
    assert (entries[3].type, entries[3].size, entries[3].modified_time) == (
        "unspecified",
        0,
        None,
    )
    sandbox.files.list("/workspace")
    assert query(rsps.calls[1]) == {"path": "/workspace"}


def test_list_of_an_empty_directory(rsps, sandbox):
    rsps.add(responses.GET, FILES + "/list", json={})
    assert sandbox.files.list("/workspace") == []


def test_get_info_and_not_found(rsps, sandbox):
    rsps.add(responses.GET, FILES + "/info", json={"entry": entry(size="1048576")})
    info = sandbox.files.get_info("/workspace/hello.txt")
    assert (info.path, info.size) == ("/workspace/hello.txt", 1048576)
    assert query(rsps.calls[0]) == {"path": "/workspace/hello.txt"}
    rsps.replace(
        responses.GET,
        FILES + "/info",
        json={"id": "not_found", "message": "file not found"},
        status=404,
    )
    with pytest.raises(NotFoundError, match="file not found"):
        sandbox.files.get_info("/workspace/missing")


def test_exists_reads_an_omitted_false(rsps, sandbox):
    rsps.add(responses.GET, FILES + "/exists", json={"exists": True})
    assert sandbox.files.exists("/workspace/hello.txt") is True
    rsps.replace(responses.GET, FILES + "/exists", json={})
    assert sandbox.files.exists("/workspace/missing") is False
    assert query(rsps.calls[1]) == {"path": "/workspace/missing"}


def test_make_dir_reads_an_omitted_created(rsps, sandbox):
    directory = entry(
        name="out", path="/workspace/out", type="FILE_ENTRY_TYPE_DIRECTORY"
    )
    rsps.add(
        responses.POST,
        FILES + "/make-directory",
        json={"created": True, "entry": directory},
    )
    result = sandbox.files.make_dir("/workspace/out")
    assert isinstance(result, MakeDirResult)
    assert (result.created, result.entry.type) == (True, "directory")
    assert body_of(rsps.calls[0]) == {"path": "/workspace/out"}
    rsps.replace(responses.POST, FILES + "/make-directory", json={"entry": directory})
    assert sandbox.files.make_dir("/workspace/out").created is False


def test_move_and_remove(rsps, sandbox):
    rsps.add(
        responses.POST,
        FILES + "/move",
        json={"entry": entry(name="new.txt", path="/workspace/new.txt")},
    )
    rsps.add(responses.POST, FILES + "/remove", json={})
    moved = sandbox.files.move("/workspace/old.txt", "/workspace/new.txt")
    assert moved.path == "/workspace/new.txt"
    assert body_of(rsps.calls[0]) == {
        "source": "/workspace/old.txt",
        "destination": "/workspace/new.txt",
    }
    assert sandbox.files.remove("/workspace/new.txt") is None
    assert body_of(rsps.calls[1]) == {"path": "/workspace/new.txt"}


def test_json_errors_are_typed(rsps, sandbox):
    rsps.add(
        responses.POST,
        FILES + "/move",
        json={"id": "bad_request", "message": "outside the workspace"},
        status=400,
    )
    with pytest.raises(InvalidRequestError, match="outside the workspace"):
        sandbox.files.move("/etc/passwd", "/workspace/x")


def test_paths_are_validated_before_sending(rsps, sandbox):
    files = sandbox.files
    calls = [
        lambda: files.write("", "x"),
        lambda: files.write_archive(" ", b"tar"),
        lambda: files.read(""),
        lambda: files.read_text(""),
        lambda: files.read_archive(""),
        lambda: files.list(""),
        lambda: files.get_info(""),
        lambda: files.exists(""),
        lambda: files.make_dir(""),
        lambda: files.remove(""),
        lambda: files.move("", "/b"),
        lambda: files.move("/a", ""),
        lambda: files.list("/a", depth=-1),
        lambda: files.write("/a", 12),
    ]
    for call in calls:
        with pytest.raises(SandboxError):
            call()
    with pytest.raises(SandboxError, match="destination"):
        files.move("/a", "")
    assert len(rsps.calls) == 0
