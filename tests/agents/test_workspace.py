# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for staged workspace transfers (sync + async)."""

from __future__ import annotations

import hashlib
import io
import json
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest

from pydo.agents import AgentsResources, WorkspaceTransferError
from pydo.aio.agents import AsyncAgentsResources

# ---------------------------------------------------------------------------
# Sync fakes
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        *,
        body: Any = None,
    ):
        self.status_code = status_code
        self.headers = {"Content-Type": "application/json"}
        self.reason = None
        if isinstance(body, (dict, list)):
            self._body_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            self._body_bytes = body.encode("utf-8")
        elif isinstance(body, bytes):
            self._body_bytes = body
        else:
            self._body_bytes = b""

    def text(self) -> str:
        return self._body_bytes.decode("utf-8")

    def body(self) -> bytes:
        return self._body_bytes

    def read(self) -> bytes:
        return self._body_bytes


class _FakePipeline:
    def __init__(self, responses: List[_FakeResponse]):
        self._responses = list(responses)
        self.calls: List[Any] = []

    def run(self, request, *, stream=False):
        self.calls.append(SimpleNamespace(request=request, stream=stream))
        return SimpleNamespace(http_response=self._responses.pop(0))


def _make_resources(responses: List[_FakeResponse]) -> AgentsResources:
    parent = MagicMock()
    parent._client = MagicMock()
    parent._client._pipeline = _FakePipeline(responses)
    return AgentsResources(
        parent, agents_endpoint="https://api.stage2.digitalocean.com"
    )


def _calls(resources) -> List[Any]:
    return resources._proxy._original._pipeline.calls


def _request_json(call) -> Any:
    # azure HttpRequest stores JSON either in .json or serializes into content
    raw = getattr(call.request, "content", None)
    if isinstance(raw, (bytes, bytearray)):
        return json.loads(raw.decode("utf-8"))
    if isinstance(raw, str):
        return json.loads(raw)
    # Some azure versions keep the dict on the request
    data = getattr(call.request, "_json", None) or getattr(call.request, "json", None)
    if isinstance(data, dict):
        return data
    # Fall back: parse from prepared body string in kwargs representation
    body = getattr(call.request, "body", None)
    if isinstance(body, (bytes, bytearray, str)):
        return json.loads(body)
    raise AssertionError(f"could not parse JSON body from {call.request!r}")


# ---------------------------------------------------------------------------
# Low-level transfer endpoints
# ---------------------------------------------------------------------------


def test_create_transfer_upload():
    resources = _make_resources(
        [
            _FakeResponse(
                201,
                body={
                    "transfer_id": "t1",
                    "direction": "upload",
                    "status": "pending",
                    "part_size": 16,
                    "upload_id": "u1",
                },
            )
        ]
    )
    resp = resources.sessions.create_transfer(
        "s1",
        direction="upload",
        path="/workspace/a.bin",
        size_bytes=32,
        sha256="abc",
        is_archive=True,
    )
    call = _calls(resources)[0]
    assert call.request.method == "POST"
    assert call.request.url.endswith("/v2/agents/sessions/s1/workspace/transfers")
    body = _request_json(call)
    assert body == {
        "direction": "upload",
        "path": "/workspace/a.bin",
        "is_archive": True,
        "size_bytes": 32,
        "sha256": "abc",
    }
    assert resp.transfer_id == "t1"
    assert resp.part_size == 16


def test_create_transfer_download():
    resources = _make_resources(
        [
            _FakeResponse(
                202,
                body={"transfer_id": "t2", "direction": "download", "status": "pending"},
            )
        ]
    )
    resp = resources.sessions.create_transfer(
        "s1", direction="download", path="dir", as_archive=True
    )
    body = _request_json(_calls(resources)[0])
    assert body == {
        "direction": "download",
        "path": "dir",
        "as_archive": True,
    }
    assert resp.transfer_id == "t2"


def test_create_part_upload_url_commit_get_cancel():
    resources = _make_resources(
        [
            _FakeResponse(
                200,
                body={
                    "transfer_id": "t1",
                    "part_urls": [
                        {
                            "part_number": 1,
                            "upload_url": "https://spaces/part1",
                        }
                    ],
                },
            ),
            _FakeResponse(
                202, body={"transfer_id": "t1", "status": "in_progress", "size_bytes": 5}
            ),
            _FakeResponse(
                200, body={"transfer_id": "t1", "status": "completed", "bytes_written": 5}
            ),
            _FakeResponse(
                200, body={"transfer_id": "t1", "aborted": True, "status": "failed"}
            ),
        ]
    )
    part = resources.sessions.create_part_upload_url("s1", "t1", part_number=1)
    assert part.upload_url == "https://spaces/part1"
    assert "/t1/part-upload-urls" in _calls(resources)[0].request.url
    assert _request_json(_calls(resources)[0]) == {"part_numbers": [1]}

    committed = resources.sessions.commit_upload("s1", "t1", sha256="deadbeef")
    assert committed.status == "in_progress"
    assert _request_json(_calls(resources)[1]) == {"sha256": "deadbeef"}

    got = resources.sessions.get_transfer("s1", "t1")
    assert got.status == "completed"

    cancelled = resources.sessions.cancel_transfer("s1", "t1", reason="stop")
    assert cancelled.aborted is True
    assert _request_json(_calls(resources)[3]) == {"reason": "stop"}


def test_create_part_upload_urls_batch():
    resources = _make_resources(
        [
            _FakeResponse(
                200,
                body={
                    "transfer_id": "t1",
                    "part_urls": [
                        {"part_number": 1, "upload_url": "https://spaces/p1"},
                        {"part_number": 2, "upload_url": "https://spaces/p2"},
                    ],
                },
            )
        ]
    )
    resp = resources.sessions.create_part_upload_urls(
        "s1", "t1", part_numbers=[1, 2]
    )
    assert _request_json(_calls(resources)[0]) == {"part_numbers": [1, 2]}
    assert len(resp.part_urls) == 2
    assert resp.part_urls[0].upload_url == "https://spaces/p1"


# ---------------------------------------------------------------------------
# High-level upload (staged)
# ---------------------------------------------------------------------------


def test_workspace_upload_multipart_flow():
    payload = b"abcdefghijklmnop"  # 16 bytes → 2 parts of part_size=8
    digest = hashlib.sha256(payload).hexdigest()
    resources = _make_resources(
        [
            _FakeResponse(
                201,
                body={
                    "transfer_id": "t1",
                    "direction": "upload",
                    "status": "pending",
                    "part_size": 8,
                },
            ),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "t1",
                    "part_urls": [
                        {"part_number": 1, "upload_url": "https://spaces/p1"},
                        {"part_number": 2, "upload_url": "https://spaces/p2"},
                    ],
                },
            ),
            _FakeResponse(202, body={"transfer_id": "t1", "status": "in_progress"}),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "t1",
                    "status": "completed",
                    "bytes_written": len(payload),
                    "sha256": digest,
                },
            ),
        ]
    )

    puts: List[Any] = []

    def _fake_put(url, data):
        puts.append((url, data))

    with patch("pydo.agents.custom_sessions._http_put_bytes", side_effect=_fake_put):
        resp = resources.sessions.workspace_upload(
            "s1", path="a.bin", data=payload, poll_interval=0.01
        )

    assert resp.status == "completed"
    assert resp.bytes_written == len(payload)
    assert resp.path == "a.bin"
    assert puts == [("https://spaces/p1", b"abcdefgh"), ("https://spaces/p2", b"ijklmnop")]

    urls = [c.request.url for c in _calls(resources)]
    assert urls[0].endswith("/workspace/transfers")
    assert urls[1].endswith("/transfers/t1/part-upload-urls")
    assert urls[2].endswith("/transfers/t1/commit")
    assert urls[3].endswith("/transfers/t1")
    assert _request_json(_calls(resources)[1]) == {"part_numbers": [1, 2]}
    assert _request_json(_calls(resources)[2])["sha256"] == digest


def test_workspace_upload_accepts_filesystem_path(tmp_path):
    payload = b"file-on-disk"
    src = tmp_path / "input.bin"
    src.write_bytes(payload)
    resources = _make_resources(
        [
            _FakeResponse(
                201,
                body={
                    "transfer_id": "t1",
                    "status": "pending",
                    "part_size": 1024,
                    "direction": "upload",
                },
            ),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "t1",
                    "part_urls": [
                        {"part_number": 1, "upload_url": "https://s/p"},
                    ],
                },
            ),
            _FakeResponse(202, body={"transfer_id": "t1", "status": "in_progress"}),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "t1",
                    "status": "completed",
                    "bytes_written": len(payload),
                },
            ),
        ]
    )
    with patch("pydo.agents.custom_sessions._http_put_bytes") as put:
        resources.sessions.workspace_upload(
            "s1", path="dest.bin", data=str(src), poll_interval=0.01
        )
    assert put.call_args[0][1] == payload


def test_workspace_upload_rejects_over_50_gib():
    class _HugeStream:
        def __init__(self):
            self._pos = 0

        def tell(self):
            return self._pos

        def seek(self, offset, whence=io.SEEK_SET):
            if whence == io.SEEK_END:
                self._pos = 50 * 1024 * 1024 * 1024 + 1
            else:
                self._pos = offset
            return self._pos

        def read(self, *_a, **_k):
            return b""

    resources = _make_resources([])
    with pytest.raises(ValueError, match="50 GiB"):
        resources.sessions.workspace_upload("s1", path="big", data=_HugeStream())


def test_workspace_upload_requires_path():
    resources = _make_resources([])
    with pytest.raises(ValueError, match="path is required"):
        resources.sessions.workspace_upload("s1", path="", data=b"x")


# ---------------------------------------------------------------------------
# High-level download (staged)
# ---------------------------------------------------------------------------


def test_workspace_download_polls_and_fetches_url():
    payload = b"hello workspace"
    digest = hashlib.sha256(payload).hexdigest()
    resources = _make_resources(
        [
            _FakeResponse(
                202,
                body={"transfer_id": "td", "direction": "download", "status": "pending"},
            ),
            _FakeResponse(
                200, body={"transfer_id": "td", "status": "pending"}
            ),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "td",
                    "direction": "download",
                    "status": "completed",
                    "bytes_written": len(payload),
                    "sha256": digest,
                    "download_url": "https://spaces/dl",
                },
            ),
        ]
    )

    with patch(
        "pydo.agents.custom_sessions._http_get_iter",
        return_value=iter([b"hello ", b"workspace"]),
    ):
        download = resources.sessions.workspace_download(
            "s1", path="out.txt", poll_interval=0.01
        )
        data = download.read()

    assert data == payload
    assert download.bytes_read == len(payload)
    assert download.size_hint == len(payload)
    assert download.expected_sha256 == digest
    assert download.is_archive is False
    assert download.transfer_id == "td"

    urls = [c.request.url for c in _calls(resources)]
    assert urls[0].endswith("/workspace/transfers")
    assert _request_json(_calls(resources)[0])["direction"] == "download"
    assert urls[-1].endswith("/transfers/td")


def test_workspace_download_archive_flag():
    payload = b"tarbytes"
    digest = hashlib.sha256(payload).hexdigest()
    resources = _make_resources(
        [
            _FakeResponse(
                202, body={"transfer_id": "td", "direction": "download", "status": "pending"}
            ),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "td",
                    "status": "completed",
                    "bytes_written": len(payload),
                    "sha256": digest,
                    "download_url": "https://spaces/dl",
                },
            ),
        ]
    )
    with patch(
        "pydo.agents.custom_sessions._http_get_iter", return_value=iter([payload])
    ):
        download = resources.sessions.workspace_download(
            "s1", path="dir", as_archive=True, poll_interval=0.01
        )
        assert download.read() == payload
        assert download.is_archive is True
    assert _request_json(_calls(resources)[0])["as_archive"] is True


def test_workspace_download_sha_mismatch():
    resources = _make_resources(
        [
            _FakeResponse(
                202, body={"transfer_id": "td", "direction": "download", "status": "pending"}
            ),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "td",
                    "status": "completed",
                    "bytes_written": 3,
                    "sha256": "0" * 64,
                    "download_url": "https://spaces/dl",
                },
            ),
        ]
    )
    with patch(
        "pydo.agents.custom_sessions._http_get_iter", return_value=iter([b"abc"])
    ):
        download = resources.sessions.workspace_download(
            "s1", path="x", poll_interval=0.01
        )
        with pytest.raises(WorkspaceTransferError, match="mismatch"):
            download.read()


def test_workspace_download_missing_sha_strict():
    resources = _make_resources(
        [
            _FakeResponse(
                202, body={"transfer_id": "td", "direction": "download", "status": "pending"}
            ),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "td",
                    "status": "completed",
                    "bytes_written": 1,
                    "download_url": "https://spaces/dl",
                },
            ),
        ]
    )
    with patch(
        "pydo.agents.custom_sessions._http_get_iter", return_value=iter([b"x"])
    ):
        download = resources.sessions.workspace_download(
            "s1", path="x", require_checksum=True, poll_interval=0.01
        )
        with pytest.raises(WorkspaceTransferError, match="sha256"):
            download.read()


def test_workspace_download_save_discards_on_failure(tmp_path):
    good = tmp_path / "good.bin"
    payload = b"good-payload"
    digest = hashlib.sha256(payload).hexdigest()
    resources = _make_resources(
        [
            _FakeResponse(
                202, body={"transfer_id": "td", "direction": "download", "status": "pending"}
            ),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "td",
                    "status": "completed",
                    "bytes_written": len(payload),
                    "sha256": digest,
                    "download_url": "https://spaces/dl",
                },
            ),
        ]
    )
    with patch(
        "pydo.agents.custom_sessions._http_get_iter", return_value=iter([payload])
    ):
        written = resources.sessions.workspace_download(
            "s1", path="g", poll_interval=0.01
        ).save(str(good))
    assert written == len(payload)
    assert good.read_bytes() == payload

    bad = tmp_path / "bad.bin"
    resources = _make_resources(
        [
            _FakeResponse(
                202, body={"transfer_id": "td", "direction": "download", "status": "pending"}
            ),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "td",
                    "status": "completed",
                    "bytes_written": 3,
                    "sha256": "0" * 64,
                    "download_url": "https://spaces/dl",
                },
            ),
        ]
    )
    with patch(
        "pydo.agents.custom_sessions._http_get_iter", return_value=iter([b"abc"])
    ):
        with pytest.raises(WorkspaceTransferError):
            resources.sessions.workspace_download(
                "s1", path="b", poll_interval=0.01
            ).save(str(bad))
    assert not bad.exists()


def test_workspace_download_failed_transfer():
    resources = _make_resources(
        [
            _FakeResponse(
                202, body={"transfer_id": "td", "direction": "download", "status": "pending"}
            ),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "td",
                    "status": "failed",
                    "error_message": "not found in workspace",
                },
            ),
            # cancel best-effort
            _FakeResponse(
                200, body={"transfer_id": "td", "aborted": False, "status": "failed"}
            ),
        ]
    )
    with pytest.raises(WorkspaceTransferError, match="not found"):
        resources.sessions.workspace_download("s1", path="missing", poll_interval=0.01)


def test_agent_session_upload_download_passthrough():
    payload = b"round-trip"
    digest = hashlib.sha256(payload).hexdigest()
    resources = _make_resources(
        [
            _FakeResponse(
                201,
                body={
                    "transfer_id": "tu",
                    "status": "pending",
                    "part_size": 1024,
                    "direction": "upload",
                },
            ),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "tu",
                    "part_urls": [
                        {"part_number": 1, "upload_url": "https://spaces/p"},
                    ],
                },
            ),
            _FakeResponse(202, body={"transfer_id": "tu", "status": "in_progress"}),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "tu",
                    "status": "completed",
                    "bytes_written": len(payload),
                },
            ),
            _FakeResponse(
                202,
                body={"transfer_id": "td", "direction": "download", "status": "pending"},
            ),
            _FakeResponse(
                200,
                body={
                    "transfer_id": "td",
                    "status": "completed",
                    "bytes_written": len(payload),
                    "sha256": digest,
                    "download_url": "https://spaces/dl",
                },
            ),
        ]
    )
    agent = resources.attach("s1")
    with patch("pydo.agents.custom_sessions._http_put_bytes"), patch(
        "pydo.agents.custom_sessions._http_get_iter", return_value=iter([payload])
    ):
        up = agent.upload_file(path="f.bin", data=payload, poll_interval=0.01)
        assert up.bytes_written == len(payload)
        assert (
            agent.download_file(path="f.bin", poll_interval=0.01).read() == payload
        )


# ---------------------------------------------------------------------------
# Async
# ---------------------------------------------------------------------------


class _FakeAsyncResponse:
    def __init__(self, status_code: int, *, body: Any = None):
        self.status_code = status_code
        self.headers = {"Content-Type": "application/json"}
        self.reason = None
        if isinstance(body, (dict, list)):
            self._body_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            self._body_bytes = body.encode("utf-8")
        elif isinstance(body, bytes):
            self._body_bytes = body
        else:
            self._body_bytes = b""

    async def read(self) -> bytes:
        return self._body_bytes

    def text(self) -> str:
        return self._body_bytes.decode("utf-8")

    def body(self) -> bytes:
        return self._body_bytes


class _FakeAsyncPipeline:
    def __init__(self, responses: List[_FakeAsyncResponse]):
        self._responses = list(responses)
        self.calls: List[Any] = []

    async def run(self, request, *, stream=False):
        self.calls.append(SimpleNamespace(request=request, stream=stream))
        return SimpleNamespace(http_response=self._responses.pop(0))


def _make_async_resources(responses: List[_FakeAsyncResponse]) -> AsyncAgentsResources:
    parent = MagicMock()
    parent._client = MagicMock()
    parent._client._pipeline = _FakeAsyncPipeline(responses)
    return AsyncAgentsResources(
        parent, agents_endpoint="https://api.stage2.digitalocean.com"
    )


@pytest.mark.asyncio
async def test_async_workspace_upload():
    payload = b"abc"
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(
                201,
                body={
                    "transfer_id": "t1",
                    "status": "pending",
                    "part_size": 1024,
                    "direction": "upload",
                },
            ),
            _FakeAsyncResponse(
                200,
                body={
                    "transfer_id": "t1",
                    "part_urls": [
                        {"part_number": 1, "upload_url": "https://spaces/p"},
                    ],
                },
            ),
            _FakeAsyncResponse(
                202, body={"transfer_id": "t1", "status": "in_progress"}
            ),
            _FakeAsyncResponse(
                200,
                body={
                    "transfer_id": "t1",
                    "status": "completed",
                    "bytes_written": 3,
                },
            ),
        ]
    )
    with patch(
        "pydo.aio.agents.custom_sessions._aio_http_put_bytes",
        return_value=None,
    ) as put:
        resp = await resources.sessions.workspace_upload(
            "s1", path="a.txt", data=payload, content_sha256="cafe", poll_interval=0.01
        )
    assert resp.bytes_written == 3
    put.assert_awaited_once()
    create_body = _request_json(resources._proxy._original._pipeline.calls[0])
    assert create_body["sha256"] == "cafe"
    assert "/workspace/transfers" in resources._proxy._original._pipeline.calls[0].request.url
    assert _request_json(resources._proxy._original._pipeline.calls[1]) == {
        "part_numbers": [1]
    }


@pytest.mark.asyncio
async def test_async_workspace_download():
    payload = b"async-bytes"
    digest = hashlib.sha256(payload).hexdigest()
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(
                202,
                body={"transfer_id": "td", "direction": "download", "status": "pending"},
            ),
            _FakeAsyncResponse(
                200,
                body={
                    "transfer_id": "td",
                    "status": "completed",
                    "bytes_written": len(payload),
                    "sha256": digest,
                    "download_url": "https://spaces/dl",
                },
            ),
        ]
    )

    async def _fake_get(_url):
        for chunk in (b"async-", b"bytes"):
            yield chunk

    with patch(
        "pydo.aio.agents.custom_sessions._aio_http_get_iter",
        side_effect=lambda url: _fake_get(url),
    ):
        download = await resources.sessions.workspace_download(
            "s1", path="o", poll_interval=0.01
        )
        data = await download.read()
    assert data == payload
    assert download.bytes_read == len(payload)


@pytest.mark.asyncio
async def test_async_download_save_discards_on_failure(tmp_path):
    bad = tmp_path / "bad.bin"
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(
                202,
                body={"transfer_id": "td", "direction": "download", "status": "pending"},
            ),
            _FakeAsyncResponse(
                200,
                body={
                    "transfer_id": "td",
                    "status": "completed",
                    "bytes_written": 3,
                    "sha256": "0" * 64,
                    "download_url": "https://spaces/dl",
                },
            ),
        ]
    )

    async def _fake_get(_url):
        yield b"abc"

    with patch(
        "pydo.aio.agents.custom_sessions._aio_http_get_iter",
        side_effect=lambda url: _fake_get(url),
    ):
        download = await resources.sessions.workspace_download(
            "s1", path="b", poll_interval=0.01
        )
        with pytest.raises(WorkspaceTransferError):
            await download.save(str(bad))
    assert not bad.exists()
