# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for workspace upload/download (sync + async)."""

from __future__ import annotations

import hashlib
import io
import json
from types import SimpleNamespace
from typing import Any, List, Optional
from unittest.mock import MagicMock

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
        chunks: Optional[List[bytes]] = None,
        headers: Optional[dict] = None,
        trailer: Optional[str] = None,
    ):
        self.status_code = status_code
        self.headers = dict(headers or {})
        self.reason = None
        self._chunks = list(chunks or [])
        self._trailer = trailer
        self.closed = False
        if isinstance(body, (dict, list)):
            self._body_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            self._body_bytes = body.encode("utf-8")
        elif isinstance(body, bytes):
            self._body_bytes = body
        else:
            self._body_bytes = b"".join(self._chunks)

    def text(self) -> str:
        return self._body_bytes.decode("utf-8")

    def body(self) -> bytes:
        return self._body_bytes

    def read(self) -> bytes:
        return self._body_bytes

    def iter_bytes(self):
        for chunk in self._chunks:
            yield chunk
        # The integrity digest is a trailer: only visible once the body is done.
        if self._trailer is not None:
            self.headers["X-Content-Sha256"] = self._trailer

    def close(self) -> None:
        self.closed = True


class _FakePipeline:
    def __init__(self, responses: List[_FakeResponse]):
        self._responses = list(responses)
        self.calls: List[Any] = []

    def run(self, request, *, stream=False):
        # The real transport reads a streamed request body here, before the
        # caller closes any opened file handle; mirror that so tests can inspect
        # the bytes that were actually sent.
        content_bytes = request.content
        if hasattr(content_bytes, "read"):
            content_bytes = content_bytes.read()
        self.calls.append(
            SimpleNamespace(request=request, stream=stream, content_bytes=content_bytes)
        )
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


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


def test_upload_bytes_sets_path_params_and_content_type():
    resources = _make_resources(
        [_FakeResponse(200, body={"path": "/workspace/a.txt", "bytes_written": 5})]
    )

    resp = resources.sessions.workspace_upload("s1", path="a.txt", data=b"hello")

    call = _calls(resources)[0]
    assert call.request.method == "POST"
    assert "/v2/agents/sessions/s1/workspace/upload" in call.request.url
    assert "path=a.txt" in call.request.url
    assert "is_archive=false" in call.request.url
    assert call.request.headers.get("Content-Type") == "application/octet-stream"
    assert "X-Content-Sha256" not in call.request.headers
    assert call.request.content == b"hello"
    assert resp.bytes_written == 5


def test_upload_forwards_sha256_header_and_is_archive():
    resources = _make_resources([_FakeResponse(200, body={"bytes_written": 3})])

    resources.sessions.workspace_upload(
        "s1",
        path="dir",
        data=b"tar",
        is_archive=True,
        content_sha256="deadbeef",
    )

    call = _calls(resources)[0]
    assert "is_archive=true" in call.request.url
    assert call.request.headers.get("X-Content-Sha256") == "deadbeef"


def test_upload_accepts_filesystem_path(tmp_path):
    payload = b"file-on-disk"
    src = tmp_path / "input.bin"
    src.write_bytes(payload)
    resources = _make_resources(
        [_FakeResponse(200, body={"bytes_written": len(payload)})]
    )

    resources.sessions.workspace_upload("s1", path="dest.bin", data=str(src))

    assert _calls(resources)[0].content_bytes == payload


def test_upload_rejects_payload_over_500_mib():
    class _HugeStream:
        def __init__(self):
            self._pos = 0

        def tell(self):
            return self._pos

        def seek(self, offset, whence=io.SEEK_SET):
            self._pos = (500 * 1024 * 1024 + 1) if whence == io.SEEK_END else offset
            return self._pos

        def read(self, *_a, **_k):
            return b""

    resources = _make_resources([])
    with pytest.raises(ValueError, match="500 MiB"):
        resources.sessions.workspace_upload("s1", path="big", data=_HugeStream())


def test_upload_requires_path():
    resources = _make_resources([])
    with pytest.raises(ValueError, match="path is required"):
        resources.sessions.workspace_upload("s1", path="", data=b"x")


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def test_download_verifies_matching_trailer_and_returns_bytes():
    payload = b"hello workspace"
    digest = hashlib.sha256(payload).hexdigest()
    resources = _make_resources(
        [
            _FakeResponse(
                200,
                chunks=[b"hello ", b"workspace"],
                headers={"X-Workspace-Size-Bytes": str(len(payload))},
                trailer=digest,
            )
        ]
    )

    download = resources.sessions.workspace_download("s1", path="out.txt")
    assert download.size_hint == len(payload)
    assert download.is_archive is False

    data = download.read()
    assert data == payload
    assert download.bytes_read == len(payload)

    call = _calls(resources)[0]
    assert call.request.method == "GET"
    assert "/v2/agents/sessions/s1/workspace/download" in call.request.url
    assert "path=out.txt" in call.request.url
    assert "as_archive=false" in call.request.url


def test_download_archive_flag_and_header():
    payload = b"tarbytes"
    resources = _make_resources(
        [
            _FakeResponse(
                200,
                chunks=[payload],
                headers={"X-Workspace-Is-Archive": "true"},
                trailer=hashlib.sha256(payload).hexdigest(),
            )
        ]
    )

    download = resources.sessions.workspace_download("s1", path="dir", as_archive=True)
    assert download.read() == payload
    assert download.is_archive is True
    assert "as_archive=true" in _calls(resources)[0].request.url


def test_download_missing_trailer_strict_mode_is_failure():
    payload = b"truncated"
    resources = _make_resources([_FakeResponse(200, chunks=[payload], trailer=None)])

    download = resources.sessions.workspace_download(
        "s1", path="x", require_checksum=True
    )
    with pytest.raises(WorkspaceTransferError, match="trailer"):
        download.read()


def test_download_missing_trailer_default_warns_and_returns():
    # Python's HTTP stack discards chunked trailers, so the default tolerates a
    # missing trailer (with a warning) rather than failing every real download.
    payload = b"no-trailer"
    resources = _make_resources([_FakeResponse(200, chunks=[payload], trailer=None)])

    download = resources.sessions.workspace_download("s1", path="x")
    with pytest.warns(UserWarning, match="X-Content-Sha256"):
        data = download.read()
    assert data == payload


def test_download_size_hint_mismatch_is_truncation_failure():
    resources = _make_resources(
        [
            _FakeResponse(
                200,
                chunks=[b"abc"],
                headers={"X-Workspace-Size-Bytes": "99"},
                trailer=None,
            )
        ]
    )
    download = resources.sessions.workspace_download("s1", path="x")
    with pytest.raises(WorkspaceTransferError, match="truncated"):
        download.read()


def test_download_size_hint_match_is_accepted():
    payload = b"sized"
    resources = _make_resources(
        [
            _FakeResponse(
                200,
                chunks=[payload],
                headers={"X-Workspace-Size-Bytes": str(len(payload))},
                trailer=None,
            )
        ]
    )
    download = resources.sessions.workspace_download("s1", path="x")
    assert download.read() == payload


def test_download_mismatched_trailer_is_failure():
    resources = _make_resources([_FakeResponse(200, chunks=[b"abc"], trailer="0" * 64)])

    download = resources.sessions.workspace_download("s1", path="x")
    with pytest.raises(WorkspaceTransferError, match="mismatch"):
        download.read()


def test_download_require_checksum_false_skips_verification():
    resources = _make_resources([_FakeResponse(200, chunks=[b"abc"], trailer=None)])

    download = resources.sessions.workspace_download(
        "s1", path="x", require_checksum=False
    )
    assert download.read() == b"abc"


def test_download_save_writes_file_and_discards_on_failure(tmp_path):
    good = tmp_path / "good.bin"
    payload = b"good-payload"
    resources = _make_resources(
        [
            _FakeResponse(
                200, chunks=[payload], trailer=hashlib.sha256(payload).hexdigest()
            )
        ]
    )
    written = resources.sessions.workspace_download("s1", path="g").save(str(good))
    assert written == len(payload)
    assert good.read_bytes() == payload

    bad = tmp_path / "bad.bin"
    resources = _make_resources([_FakeResponse(200, chunks=[b"abc"], trailer="0" * 64)])
    with pytest.raises(WorkspaceTransferError):
        resources.sessions.workspace_download("s1", path="b").save(str(bad))
    assert not bad.exists()


def test_download_non_200_raises():
    from azure.core.exceptions import HttpResponseError

    resources = _make_resources([_FakeResponse(404, body="path not found")])
    with pytest.raises(HttpResponseError):
        resources.sessions.workspace_download("s1", path="missing")


def test_agent_session_upload_download_passthrough(tmp_path):
    payload = b"round-trip"
    resources = _make_resources(
        [
            _FakeResponse(200, body={"bytes_written": len(payload)}),
            _FakeResponse(
                200, chunks=[payload], trailer=hashlib.sha256(payload).hexdigest()
            ),
        ]
    )
    agent = resources.attach("s1")

    up = agent.upload_file(path="f.bin", data=payload)
    assert up.bytes_written == len(payload)
    assert agent.download_file(path="f.bin").read() == payload


# ---------------------------------------------------------------------------
# Async fakes + tests
# ---------------------------------------------------------------------------


class _FakeAsyncResponse:
    def __init__(
        self,
        status_code: int,
        *,
        body: Any = None,
        chunks: Optional[List[bytes]] = None,
        headers: Optional[dict] = None,
        trailer: Optional[str] = None,
    ):
        self.status_code = status_code
        self.headers = dict(headers or {})
        self.reason = None
        self._chunks = list(chunks or [])
        self._trailer = trailer
        if isinstance(body, (dict, list)):
            self._body_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            self._body_bytes = body.encode("utf-8")
        elif isinstance(body, bytes):
            self._body_bytes = body
        else:
            self._body_bytes = b"".join(self._chunks)

    async def read(self) -> bytes:
        return self._body_bytes

    def text(self) -> str:
        return self._body_bytes.decode("utf-8")

    def body(self) -> bytes:
        return self._body_bytes

    async def iter_bytes(self):
        for chunk in self._chunks:
            yield chunk
        if self._trailer is not None:
            self.headers["X-Content-Sha256"] = self._trailer

    def close(self) -> None:
        pass


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
async def test_async_upload_materializes_and_sets_headers():
    resources = _make_async_resources(
        [_FakeAsyncResponse(200, body={"bytes_written": 3})]
    )

    resp = await resources.sessions.workspace_upload(
        "s1", path="a.txt", data=b"abc", content_sha256="cafe"
    )

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "POST"
    assert "/v2/agents/sessions/s1/workspace/upload" in call.request.url
    assert call.request.headers.get("Content-Type") == "application/octet-stream"
    assert call.request.headers.get("X-Content-Sha256") == "cafe"
    assert resp.bytes_written == 3


@pytest.mark.asyncio
async def test_async_download_verifies_trailer():
    payload = b"async-bytes"
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(
                200,
                chunks=[b"async-", b"bytes"],
                trailer=hashlib.sha256(payload).hexdigest(),
            )
        ]
    )

    download = await resources.sessions.workspace_download("s1", path="o")
    data = await download.read()
    assert data == payload
    assert download.bytes_read == len(payload)


@pytest.mark.asyncio
async def test_async_download_missing_trailer_strict_fails():
    resources = _make_async_resources(
        [_FakeAsyncResponse(200, chunks=[b"x"], trailer=None)]
    )

    download = await resources.sessions.workspace_download(
        "s1", path="o", require_checksum=True
    )
    with pytest.raises(WorkspaceTransferError):
        await download.read()


@pytest.mark.asyncio
async def test_async_download_save_discards_on_failure(tmp_path):
    bad = tmp_path / "bad.bin"
    resources = _make_async_resources(
        [_FakeAsyncResponse(200, chunks=[b"abc"], trailer="0" * 64)]
    )
    download = await resources.sessions.workspace_download("s1", path="b")
    with pytest.raises(WorkspaceTransferError):
        await download.save(str(bad))
    assert not bad.exists()
