# pylint: disable=missing-function-docstring,redefined-outer-name,duplicate-code,invalid-name,unbalanced-tuple-unpacking
"""Mocked tests for async sandbox files (``pydo.aio.sandbox``).

Runs through the real async pipeline, with aioresponses.
"""

import hashlib
import json
import re
from types import SimpleNamespace
from urllib.parse import parse_qs, unquote, urlparse

import pytest
import pytest_asyncio
from aioresponses import aioresponses

from pydo.aio.sandbox import (
    FileEntry,
    NotFoundError,
    Sandbox,
    SandboxError,
    ServiceError,
    WriteInfo,
)
from pydo.aio.sandbox import files as files_module

pytestmark = pytest.mark.asyncio

API = "https://sandbox.test"
CONN = {"token": "test-token", "api_url": API}


def route(name):
    return re.compile(rf"^{re.escape(API)}/v2/sandboxes/sb-1/files/{name}(\?.*)?$")


def entry(**extra):
    out = {
        "name": "hello.txt",
        "type": "FILE_ENTRY_TYPE_FILE",
        "path": "/workspace/hello.txt",
        "size": "12",
        "mode": 420,
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
def sleeps(monkeypatch):
    waited = []

    async def sleep(delay):
        waited.append(delay)

    monkeypatch.setattr(files_module, "asyncio", SimpleNamespace(sleep=sleep))
    return waited


@pytest.fixture
def mock():
    with aioresponses() as m:
        yield m


@pytest_asyncio.fixture
async def sandbox(mock):
    mock.get(
        API + "/v2/sandboxes/sb-1",
        payload={
            "sandbox": {
                "sandbox_id": "sb-1",
                "template": "coding-base",
                "state": "SANDBOX_STATE_RUNNING",
            }
        },
    )
    sb = await Sandbox.get("sb-1", **CONN)
    mock.requests.clear()
    yield sb
    await sb.close()


def sent(mock, name):
    """Every request sent to one files route, in order: (query, kwargs)."""
    out = []
    for (_method, url), calls in mock.requests.items():
        if urlparse(str(url)).path.endswith("/files/" + name):
            # aioresponses may leave path query values percent-encoded.
            query = {
                k: unquote(v[0]) for k, v in parse_qs(urlparse(str(url)).query).items()
            }
            out.extend((query, call.kwargs) for call in calls)
    return out


def body(kwargs):
    return kwargs.get("data")


async def test_write_sends_raw_bytes_and_their_sha256(mock, sandbox):
    mock.post(route("upload"), payload={"path": "/workspace/a", "bytes_written": "5"})
    info = await sandbox.files.write("/workspace/a", "hello")
    assert info == WriteInfo(path="/workspace/a", bytes_written=5)
    [(query, kwargs)] = sent(mock, "upload")
    assert query == {"path": "/workspace/a"}
    assert body(kwargs) == b"hello"
    headers = {k.lower(): v for k, v in kwargs["headers"].items()}
    assert headers["content-type"] == "application/octet-stream"
    assert headers["x-content-sha256"] == hashlib.sha256(b"hello").hexdigest()


async def test_write_archive(mock, sandbox):
    mock.post(route("upload"), payload={"path": "/workspace/out", "bytes_written": "3"})
    await sandbox.files.write_archive("/workspace/out", b"tar")
    [(query, _kwargs)] = sent(mock, "upload")
    assert query == {"path": "/workspace/out", "is_archive": "true"}


async def test_read_strips_and_checks_the_footer(mock, sandbox):
    mock.get(
        route("download"),
        body=footer(b"hello\n"),
        content_type="application/octet-stream",
    )
    assert await sandbox.files.read_text("/workspace/hello.txt") == "hello\n"
    mock.get(
        route("download"),
        body=footer(b"tar"),
        content_type="application/octet-stream",
    )
    assert await sandbox.files.read_archive("/workspace/dir") == b"tar"
    queries = [q for q, _ in sent(mock, "download")]
    assert {"path": "/workspace/dir", "as_archive": "true"} in queries


async def test_read_rejects_a_mismatched_footer(mock, sandbox):
    mock.get(
        route("download"),
        body=footer(b"hello", digest="f" * 64),
        content_type="application/octet-stream",
    )
    with pytest.raises(SandboxError, match="integrity check"):
        await sandbox.files.read("/workspace/hello.txt")
    mock.get(route("download"), body=b"short", content_type="application/octet-stream")
    with pytest.raises(SandboxError, match="footer"):
        await sandbox.files.read("/workspace/hello.txt")


async def test_download_error_is_typed(mock, sandbox):
    mock.get(
        route("download"),
        status=404,
        payload={"id": "not_found", "message": "no such file"},
    )
    with pytest.raises(NotFoundError, match="no such file"):
        await sandbox.files.read("/workspace/missing")


async def test_503_is_retried_then_raised(mock, sandbox, sleeps):
    busy = {"id": "service_unavailable", "message": "Too many transfers"}
    mock.post(route("upload"), status=503, payload=busy)
    mock.post(route("upload"), payload={"path": "/a", "bytes_written": "1"})
    assert (await sandbox.files.write("/a", "x")).bytes_written == 1
    assert sleeps == [0.5]
    mock.get(route("download"), status=503, payload=busy, repeat=True)
    with pytest.raises(ServiceError, match="Too many transfers"):
        await sandbox.files.read("/a")
    assert len(sent(mock, "download")) == 4
    assert sleeps == [0.5, 0.5, 1.0, 2.0]


async def test_metadata_calls(mock, sandbox):
    mock.get(route("list"), payload={"entries": [entry()]})
    mock.get(route("info"), payload={"entry": entry()})
    mock.get(route("exists"), payload={})
    mock.post(
        route("make-directory"),
        payload={"entry": entry(type="FILE_ENTRY_TYPE_DIRECTORY", path="/w/d")},
    )
    mock.post(route("move"), payload={"entry": entry(path="/w/new.txt")})
    mock.post(route("remove"), payload={})

    [listed] = await sandbox.files.list("/workspace", depth=1)
    assert isinstance(listed, FileEntry)
    assert (listed.type, listed.size, listed.mode) == ("file", 12, 420)
    assert sent(mock, "list")[0][0] == {"path": "/workspace", "depth": "1"}
    assert (await sandbox.files.get_info("/workspace/hello.txt")).name == "hello.txt"
    assert await sandbox.files.exists("/workspace/missing") is False
    made = await sandbox.files.make_dir("/w/d")
    assert (made.created, made.entry.type) == (False, "directory")
    assert json.loads(body(sent(mock, "make-directory")[0][1])) == {"path": "/w/d"}
    assert (await sandbox.files.move("/w/old.txt", "/w/new.txt")).path == "/w/new.txt"
    assert json.loads(body(sent(mock, "move")[0][1])) == {
        "source": "/w/old.txt",
        "destination": "/w/new.txt",
    }
    assert await sandbox.files.remove("/w/new.txt") is None
    assert json.loads(body(sent(mock, "remove")[0][1])) == {"path": "/w/new.txt"}


async def test_get_info_not_found(mock, sandbox):
    mock.get(route("info"), status=404, payload={"id": "not_found", "message": "gone"})
    with pytest.raises(NotFoundError, match="gone"):
        await sandbox.files.get_info("/w/missing")


async def test_paths_are_validated_before_sending(mock, sandbox):
    files = sandbox.files
    for call in (
        files.write("", "x"),
        files.write_archive("", b""),
        files.read(""),
        files.read_text(""),
        files.read_archive(""),
        files.list(""),
        files.get_info(""),
        files.exists(""),
        files.make_dir(""),
        files.remove(""),
        files.move("", "/b"),
        files.move("/a", " "),
    ):
        with pytest.raises(SandboxError, match="required"):
            await call
    assert not mock.requests
