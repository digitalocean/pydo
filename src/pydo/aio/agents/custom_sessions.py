# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async Hosted Agents session operations."""

from __future__ import annotations

import asyncio
import hashlib
import json as _json
import os
import time
from typing import Any, AsyncIterator, BinaryIO, Dict, List, Optional, Union
from urllib.parse import quote

from azure.core.rest import HttpRequest

from pydo.agents.custom_sessions import (
    _DEFAULT_CREATE_TIMEOUT,
    _DEFAULT_POLL_INTERVAL,
    _DEFAULT_POLL_TIMEOUT,
    _DOWNLOAD_CHUNK,
    _MAX_TRANSFER_BYTES,
    _OCTET_STREAM,
    _OK_STATUS,
    _TRANSFERS_SUFFIX,
    _YAML_MEDIA_TYPE,
    HarnessStreamError,
    HistoryPage,
    UploadData,
    WorkspaceTransferError,
    _coerce_upload_content,
    _field,
    _http_get_iter,
    _http_put_bytes,
    _manifest_bytes,
    _raise_agents_http_error,
    _strip_tenant_fields,
    _unwrap_harness_sse_chunk,
    _verify_transfer_sha256,
)
from pydo.custom_extensions import AsyncSSEStream, _wrap

_BASE_PATH = "/v2/agents/sessions"


def _quote(value: str) -> str:
    return quote(str(value), safe="")


async def _run_sync(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args))


async def _aio_http_put_bytes(url: str, data: bytes) -> None:
    try:
        import aiohttp
    except ImportError:
        # Fallback for environments without the aio extra.
        await _run_sync(_http_put_bytes, url, data)
        return
    async with aiohttp.ClientSession() as session:
        async with session.put(
            url, data=data, headers={"Content-Type": _OCTET_STREAM}
        ) as resp:
            body = await resp.read()
            if resp.status not in (200, 201, 204):
                detail = body.decode("utf-8", errors="replace").strip()
                raise WorkspaceTransferError(
                    f"part upload failed: HTTP {resp.status}"
                    + (f": {detail}" if detail else "")
                )


async def _aio_http_get_iter(url: str) -> AsyncIterator[bytes]:
    try:
        import aiohttp
    except ImportError:
        chunks = await _run_sync(lambda: list(_http_get_iter(url)))
        for chunk in chunks:
            yield chunk
        return
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                detail = (await resp.text()).strip()
                raise WorkspaceTransferError(
                    f"download failed: HTTP {resp.status}"
                    + (f": {detail}" if detail else "")
                )
            async for chunk in resp.content.iter_chunked(_DOWNLOAD_CHUNK):
                if chunk:
                    yield chunk


class AsyncHarnessEventStream:
    def __init__(self, sse_stream: AsyncSSEStream):
        self._sse = sse_stream
        self.oldest_event_id: Optional[str] = None

    @property
    def has_more(self) -> Optional[bool]:
        """Whether older history remains, per the server's trailing comment.

        Only history pages (``before=``) carry this; ``None`` until the
        ``: has_more=...`` frame arrives, so read it after iterating.
        """
        return getattr(self._sse, "has_more", None)

    def __aiter__(self) -> AsyncIterator[Any]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[Any]:
        async for chunk in self._sse:
            if not isinstance(chunk, dict):
                continue
            if chunk.get("error"):
                err = chunk["error"]
                raise HarnessStreamError(
                    grpc_code=err.get("grpc_code"),
                    http_code=err.get("http_code"),
                    message=err.get("message") or "stream error",
                    http_status=err.get("http_status"),
                    details=err.get("details") or [],
                )
            event = _unwrap_harness_sse_chunk(chunk)
            if event is not None:
                if self.oldest_event_id is None:
                    event_id = _field(event, "event_id")
                    if event_id:
                        self.oldest_event_id = str(event_id)
                yield event

    async def close(self) -> None:
        await self._sse.close()

    async def __aenter__(self) -> "AsyncHarnessEventStream":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


class AsyncSessionsOperations:
    def __init__(self, base_url_proxy):
        self._client = base_url_proxy

    async def _send(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        content: Optional[Any] = None,
        content_type: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False,
        timeout: Optional[float] = None,
    ):
        headers = {"Accept": "application/json", **(headers or {})}
        kwargs: Dict[str, Any] = {"headers": headers}
        if params:
            kwargs["params"] = {
                k: v for k, v in params.items() if v is not None and v != ""
            }
        if body is not None:
            headers["Content-Type"] = "application/json"
            kwargs["json"] = body
        elif content is not None:
            if content_type:
                headers["Content-Type"] = content_type
            kwargs["content"] = content

        request = HttpRequest(method, path, **kwargs)
        request.url = self._client.format_url(request.url)
        run_kwargs: Dict[str, Any] = {"stream": stream}
        if timeout is not None:
            run_kwargs["connection_timeout"] = float(timeout)
            run_kwargs["read_timeout"] = float(timeout)
            run_kwargs["timeout"] = float(timeout)
        pipeline_response = await self._client._pipeline.run(request, **run_kwargs)
        response = pipeline_response.http_response

        if response.status_code not in _OK_STATUS:
            await response.read()
            _raise_agents_http_error(response)
        return pipeline_response

    @staticmethod
    async def _parse_json(pipeline_response) -> Any:
        body = await pipeline_response.http_response.read()
        if not body:
            return None
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        return _strip_tenant_fields(_wrap(_json.loads(body)))

    async def list(
        self,
        *,
        page_token: Optional[str] = None,
        page_size: Optional[int] = None,
        status: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Any:
        """List sessions, optionally filtered by ``status`` and/or ``name``.

        ``name`` filters server-side (``GET /v2/agents/sessions?name=...``) and
        may match more than one session (e.g. a name reused over time).
        """
        return await self._parse_json(
            await self._send(
                "GET",
                _BASE_PATH,
                params={
                    "page_token": page_token,
                    "page_size": page_size,
                    "status": status,
                    "name": name,
                },
            ),
        )

    async def create_from_manifest(
        self,
        manifest: Union[str, bytes],
        *,
        openai_session_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Create a session from an ``agents.yaml`` manifest.

        See :meth:`pydo.agents.custom_sessions.SessionsOperations.create_from_manifest`.
        """
        data = _manifest_bytes(manifest)
        params: Optional[Dict[str, Any]] = None
        if openai_session_id:
            params = {"openai_session_id": openai_session_id}
        return await self._parse_json(
            await self._send(
                "POST",
                _BASE_PATH,
                content=data,
                content_type=_YAML_MEDIA_TYPE,
                params=params,
                timeout=(
                    _DEFAULT_CREATE_TIMEOUT if timeout is None else float(timeout)
                ),
            ),
        )

    async def get(self, session_id: str) -> Any:
        return await self._parse_json(
            await self._send("GET", f"{_BASE_PATH}/{_quote(session_id)}"),
        )

    async def destroy(self, session_id: str) -> None:
        await self._send("DELETE", f"{_BASE_PATH}/{_quote(session_id)}")

    async def pause(self, session_id: str) -> Any:
        """Pause a running session (``POST .../{session_id}/pause``)."""
        return await self._parse_json(
            await self._send("POST", f"{_BASE_PATH}/{_quote(session_id)}/pause"),
        )

    async def resume(self, session_id: str) -> Any:
        """Resume a paused session (``POST .../{session_id}/resume``)."""
        return await self._parse_json(
            await self._send("POST", f"{_BASE_PATH}/{_quote(session_id)}/resume"),
        )

    async def send_input(self, session_id: str, *, text: str) -> Any:
        return await self._parse_json(
            await self._send(
                "POST",
                f"{_BASE_PATH}/{_quote(session_id)}/input",
                body={"text": text},
            ),
        )

    async def resolve_hitl(
        self,
        session_id: str,
        request_id: str,
        *,
        outcome: str,
        reason: Optional[str] = None,
        source: Optional[str] = None,
    ) -> None:
        body: Dict[str, Any] = {"outcome": outcome}
        if reason is not None:
            body["reason"] = reason
        if source is not None:
            body["source"] = source
        await self._send(
            "POST",
            f"{_BASE_PATH}/{_quote(session_id)}/hitl/{_quote(request_id)}",
            body=body,
        )

    async def start_oauth_flow(
        self,
        session_id: str,
        provider: str,
        *,
        requested_scopes: Optional[List[str]] = None,
    ) -> Any:
        body: Dict[str, Any] = {}
        if requested_scopes is not None:
            body["requested_scopes"] = list(requested_scopes)
        return await self._parse_json(
            await self._send(
                "POST",
                f"{_BASE_PATH}/{_quote(session_id)}/oauth/{_quote(provider)}",
                body=body,
            ),
        )

    async def stream(
        self,
        session_id: str,
        *,
        replay_from: Optional[str] = None,
        replay_only: bool = False,
        before: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> AsyncHarnessEventStream:
        """Attach to a session's SSE event feed.

        A cursorless attach replays only the newest events the server keeps
        within its replay budget, then goes live — it is not the session's
        full history. Older history is read a page at a time with ``before``,
        an ``event_id`` to page backwards from (exclusive): the server sends
        up to ``limit`` older events, oldest-first, then closes without going
        live. ``before`` implies ``replay_only``, which the server requires.

        Prefer :meth:`history_page` for scrollback; it drains one page and
        hands back the next cursor.
        """
        if limit is not None:
            if before is None:
                raise ValueError("limit is only meaningful together with before")
            if int(limit) < 1:
                raise ValueError("limit must be a positive integer")

        params: Dict[str, Any] = {}
        if replay_from:
            params["replay_from"] = replay_from
        if before:
            params["before"] = before
            replay_only = True
        if limit is not None:
            params["limit"] = int(limit)
        if replay_only:
            params["replay_only"] = "true"

        request = HttpRequest(
            "GET",
            f"{_BASE_PATH}/{_quote(session_id)}/stream",
            headers={"Accept": "text/event-stream, application/json"},
            params=params,
        )
        request.url = self._client.format_url(request.url)
        pipeline_response = await self._client._pipeline.run(request, stream=True)
        response = pipeline_response.http_response
        if response.status_code != 200:
            await response.read()
            _raise_agents_http_error(response)
        return AsyncHarnessEventStream(AsyncSSEStream(response))

    async def history_page(
        self,
        session_id: str,
        *,
        before: str,
        limit: Optional[int] = None,
    ) -> HistoryPage:
        """Read one page of history older than ``before``, oldest-first.

        Walk backwards by feeding ``next_before`` into the next call::

            cursor = oldest_event_id_you_hold
            while cursor:
                page = await sessions.history_page(session_id, before=cursor)
                cursor = page.next_before if page.has_more else None
        """
        if not before:
            raise ValueError("before is required")
        stream = await self.stream(session_id, before=before, limit=limit)
        async with stream:
            events = [event async for event in stream]
        return HistoryPage(
            events=events,
            has_more=stream.has_more,
            next_before=stream.oldest_event_id,
        )

    def _transfers_path(self, session_id: str, *parts: str) -> str:
        path = f"{_BASE_PATH}/{_quote(session_id)}/{_TRANSFERS_SUFFIX}"
        for part in parts:
            path = f"{path}/{_quote(part)}"
        return path

    async def create_transfer(
        self,
        session_id: str,
        *,
        direction: str,
        path: str,
        is_archive: bool = False,
        as_archive: bool = False,
        size_bytes: Optional[int] = None,
        sha256: Optional[str] = None,
    ) -> Any:
        """Start a staged workspace transfer (``POST .../workspace/transfers``)."""
        if not path:
            raise ValueError("path is required")
        if direction not in ("upload", "download"):
            raise ValueError('direction must be "upload" or "download"')
        body: Dict[str, Any] = {"direction": direction, "path": path}
        if direction == "upload":
            body["is_archive"] = bool(is_archive)
            if size_bytes is not None:
                body["size_bytes"] = int(size_bytes)
            if sha256 is not None:
                body["sha256"] = sha256
        else:
            body["as_archive"] = bool(as_archive)
        return await self._parse_json(
            await self._send("POST", self._transfers_path(session_id), body=body),
        )

    async def create_part_upload_urls(
        self,
        session_id: str,
        transfer_id: str,
        *,
        part_numbers: List[int],
    ) -> Any:
        """Get presigned URLs for one or more upload parts (upload only)."""
        numbers = [int(n) for n in part_numbers]
        if not numbers or any(n < 1 for n in numbers):
            raise ValueError("part_numbers must be a non-empty list of integers >= 1")
        return await self._parse_json(
            await self._send(
                "POST",
                self._transfers_path(session_id, transfer_id, "part-upload-urls"),
                body={"part_numbers": numbers},
            ),
        )

    async def create_part_upload_url(
        self,
        session_id: str,
        transfer_id: str,
        *,
        part_number: int,
    ) -> Any:
        """Convenience wrapper for a single part URL via the batch endpoint."""
        resp = await self.create_part_upload_urls(
            session_id, transfer_id, part_numbers=[part_number]
        )
        urls = _field(resp, "part_urls") or []
        for entry in urls:
            if int(_field(entry, "part_number") or 0) == int(part_number):
                return entry
        if len(urls) == 1:
            return urls[0]
        raise WorkspaceTransferError(
            f"CreatePartUploadURL response missing part_number={part_number}"
        )

    async def commit_upload(
        self,
        session_id: str,
        transfer_id: str,
        *,
        sha256: Optional[str] = None,
    ) -> Any:
        """Finalize uploaded parts and start applying them into the workspace."""
        body: Dict[str, Any] = {}
        if sha256 is not None:
            body["sha256"] = sha256
        return await self._parse_json(
            await self._send(
                "POST",
                self._transfers_path(session_id, transfer_id, "commit"),
                body=body,
            ),
        )

    async def get_transfer(self, session_id: str, transfer_id: str) -> Any:
        """Poll transfer status; downloads expose ``download_url`` + ``sha256``."""
        return await self._parse_json(
            await self._send("GET", self._transfers_path(session_id, transfer_id)),
        )

    async def cancel_transfer(
        self,
        session_id: str,
        transfer_id: str,
        *,
        reason: Optional[str] = None,
    ) -> Any:
        """Abort an in-flight transfer (idempotent)."""
        body: Dict[str, Any] = {}
        if reason is not None:
            body["reason"] = reason
        return await self._parse_json(
            await self._send(
                "POST",
                self._transfers_path(session_id, transfer_id, "cancel"),
                body=body,
            ),
        )

    async def wait_transfer(
        self,
        session_id: str,
        transfer_id: str,
        *,
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
        timeout: float = _DEFAULT_POLL_TIMEOUT,
    ) -> Any:
        """Poll :meth:`get_transfer` until ``completed`` or ``failed``."""
        deadline = time.monotonic() + timeout
        while True:
            info = await self.get_transfer(session_id, transfer_id)
            status = _field(info, "status")
            if status in ("completed", "failed"):
                if status == "failed":
                    message = _field(info, "error_message") or "transfer failed"
                    raise WorkspaceTransferError(str(message))
                return info
            if time.monotonic() >= deadline:
                raise WorkspaceTransferError(
                    f"transfer {transfer_id!r} timed out after {timeout:g}s "
                    f"(last status={status!r})"
                )
            await asyncio.sleep(max(poll_interval, 0.05))

    async def workspace_upload(
        self,
        session_id: str,
        *,
        path: str,
        data: UploadData,
        is_archive: bool = False,
        content_sha256: Optional[str] = None,
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
        timeout: float = _DEFAULT_POLL_TIMEOUT,
    ) -> Any:
        """Upload a file/tar via staged transfers (async).

        Async counterpart of
        :meth:`pydo.agents.custom_sessions.SessionsOperations.workspace_upload`.
        """
        if not path:
            raise ValueError("path is required")
        content, size, handle = _coerce_upload_content(data)
        try:
            # Materialize non-bytes payloads; aiohttp/part PUTs need concrete bytes.
            if hasattr(content, "read"):
                content = content.read()
                if isinstance(content, str):
                    content = content.encode("utf-8")
                size = len(content)
        finally:
            if handle is not None:
                handle.close()

        if size > _MAX_TRANSFER_BYTES:
            raise ValueError(
                f"upload of {size} bytes exceeds the 50 GiB transfer limit"
            )

        transfer_id = None
        try:
            created = await self.create_transfer(
                session_id,
                direction="upload",
                path=path,
                is_archive=is_archive,
                size_bytes=size,
                sha256=content_sha256,
            )
            transfer_id = _field(created, "transfer_id")
            part_size = int(_field(created, "part_size") or 0)
            if not transfer_id:
                raise WorkspaceTransferError(
                    "CreateTransfer response missing transfer_id"
                )
            if part_size < 1:
                raise WorkspaceTransferError(
                    "CreateTransfer response missing a positive part_size"
                )

            hasher = hashlib.sha256()
            if size == 0:
                part_url_by_number: Dict[int, str] = {}
            else:
                num_parts = (size + part_size - 1) // part_size
                part_numbers = list(range(1, num_parts + 1))
                batch = await self.create_part_upload_urls(
                    session_id, transfer_id, part_numbers=part_numbers
                )
                part_url_by_number = {}
                for entry in _field(batch, "part_urls") or []:
                    n = int(_field(entry, "part_number") or 0)
                    url = _field(entry, "upload_url")
                    if n and url:
                        part_url_by_number[n] = str(url)
                missing = [n for n in part_numbers if n not in part_url_by_number]
                if missing:
                    raise WorkspaceTransferError(
                        f"CreatePartUploadURL missing upload_url for parts {missing}"
                    )

            offset = 0
            part_number = 1
            while offset < size:
                length = min(part_size, size - offset)
                chunk = bytes(content[offset : offset + length])
                hasher.update(chunk)
                await _aio_http_put_bytes(part_url_by_number[part_number], chunk)
                offset += length
                part_number += 1

            digest = content_sha256 or hasher.hexdigest()
            await self.commit_upload(session_id, transfer_id, sha256=digest)
            completed = await self.wait_transfer(
                session_id,
                transfer_id,
                poll_interval=poll_interval,
                timeout=timeout,
            )
            if _field(completed, "path") is None and hasattr(completed, "__setitem__"):
                completed["path"] = path
            if _field(completed, "bytes_written") is None and hasattr(
                completed, "__setitem__"
            ):
                completed["bytes_written"] = size
            return completed
        except Exception:
            if transfer_id:
                try:
                    await self.cancel_transfer(
                        session_id, transfer_id, reason="client_error"
                    )
                except Exception:  # noqa: BLE001
                    pass
            raise

    async def workspace_download(
        self,
        session_id: str,
        *,
        path: str,
        as_archive: bool = False,
        require_checksum: bool = False,
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
        timeout: float = _DEFAULT_POLL_TIMEOUT,
    ) -> "AsyncWorkspaceDownload":
        """Download a workspace file/tar via staged transfers (async)."""
        if not path:
            raise ValueError("path is required")
        created = await self.create_transfer(
            session_id,
            direction="download",
            path=path,
            as_archive=as_archive,
        )
        transfer_id = _field(created, "transfer_id")
        if not transfer_id:
            raise WorkspaceTransferError("CreateTransfer response missing transfer_id")
        try:
            completed = await self.wait_transfer(
                session_id,
                transfer_id,
                poll_interval=poll_interval,
                timeout=timeout,
            )
        except Exception:
            try:
                await self.cancel_transfer(
                    session_id, transfer_id, reason="client_error"
                )
            except Exception:  # noqa: BLE001
                pass
            raise
        download_url = _field(completed, "download_url")
        if not download_url:
            raise WorkspaceTransferError(
                "completed download transfer is missing download_url"
            )
        size_hint = _field(completed, "bytes_written")
        try:
            size_hint = int(size_hint) if size_hint is not None else None
        except (TypeError, ValueError):
            size_hint = None
        return AsyncWorkspaceDownload(
            download_url=str(download_url),
            expected_sha256=_field(completed, "sha256"),
            size_hint=size_hint,
            is_archive=as_archive,
            require_checksum=require_checksum,
            transfer_id=str(transfer_id),
        )


class AsyncWorkspaceDownload:
    """Async streaming download from a completed staged transfer."""

    def __init__(
        self,
        *,
        download_url: str,
        expected_sha256: Optional[str] = None,
        size_hint: Optional[int] = None,
        is_archive: bool = False,
        require_checksum: bool = False,
        transfer_id: Optional[str] = None,
    ):
        self._download_url = download_url
        self._expected_sha256 = expected_sha256
        self._size_hint = size_hint
        self._is_archive = bool(is_archive)
        self._require_checksum = require_checksum
        self.transfer_id = transfer_id
        self.bytes_read = 0

    @property
    def is_archive(self) -> bool:
        return self._is_archive

    @property
    def size_hint(self) -> Optional[int]:
        return self._size_hint

    @property
    def expected_sha256(self) -> Optional[str]:
        return self._expected_sha256

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[bytes]:
        hasher = hashlib.sha256()
        total = 0
        async for chunk in _aio_http_get_iter(self._download_url):
            hasher.update(chunk)
            total += len(chunk)
            yield bytes(chunk)
        self.bytes_read = total
        _verify_transfer_sha256(
            hasher.hexdigest(),
            self._expected_sha256,
            total_bytes=total,
            size_hint=self._size_hint,
            require_checksum=self._require_checksum,
        )

    async def read(self) -> bytes:
        chunks = [chunk async for chunk in self]
        return b"".join(chunks)

    async def save(self, dest: Union[str, "os.PathLike[str]", BinaryIO]) -> int:
        own = isinstance(dest, (str, os.PathLike))
        handle = open(os.fspath(dest), "wb") if own else dest  # type: ignore[arg-type]
        total = 0
        try:
            async for chunk in self:
                handle.write(chunk)
                total += len(chunk)
        except WorkspaceTransferError:
            if own:
                handle.close()
                try:
                    os.remove(os.fspath(dest))  # type: ignore[arg-type]
                except OSError:
                    pass
            raise
        finally:
            if own and not handle.closed:
                handle.close()
        return total

    async def close(self) -> None:
        return None

    async def __aenter__(self) -> "AsyncWorkspaceDownload":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


__all__ = [
    "AsyncSessionsOperations",
    "AsyncHarnessEventStream",
    "AsyncWorkspaceDownload",
]
