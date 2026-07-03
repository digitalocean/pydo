# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async Hosted Agents session operations."""

from __future__ import annotations

import hashlib
import json as _json
import os
from typing import Any, AsyncIterator, BinaryIO, Dict, List, Optional, Union
from urllib.parse import quote

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
    ResourceNotModifiedError,
    map_error,
)
from azure.core.rest import HttpRequest

from pydo.agents.custom_sessions import (
    _MAX_UPLOAD_BYTES,
    _OCTET_STREAM,
    _SHA256_HEADER,
    _YAML_MEDIA_TYPE,
    HarnessStreamError,
    UploadData,
    WorkspaceTransferError,
    _bool_param,
    _coerce_upload_content,
    _download_is_archive,
    _download_size_hint,
    _manifest_bytes,
    _raise_agents_http_error,
    _unwrap_harness_sse_chunk,
    _verify_download,
)
from pydo.custom_extensions import AsyncSSEStream, _wrap

_ERROR_MAP = {
    401: ClientAuthenticationError,
    404: ResourceNotFoundError,
    409: ResourceExistsError,
    304: ResourceNotModifiedError,
}

_BASE_PATH = "/v2/agents/sessions"


def _quote(value: str) -> str:
    return quote(str(value), safe="")


class AsyncHarnessEventStream:
    def __init__(self, sse_stream: AsyncSSEStream):
        self._sse = sse_stream

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
        pipeline_response = await self._client._pipeline.run(request, stream=stream)
        response = pipeline_response.http_response

        if response.status_code not in (200, 204):
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
        return _wrap(_json.loads(body))

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

    async def create_from_manifest(self, manifest: Union[str, bytes]) -> Any:
        """Create a session from an ``agents.yaml`` manifest.

        This is the supported creation path: the manifest defines everything
        about the session (runtime adapter, sandbox, env vars, egress). It is
        uploaded verbatim as ``application/x-yaml`` and the server owns parsing
        and validation. There are no ``agent_kind``/``repo_hint`` arguments.

        :param manifest: The agent spec as a YAML ``str`` or ``bytes`` document.
        """
        data = _manifest_bytes(manifest)
        return await self._parse_json(
            await self._send(
                "POST",
                _BASE_PATH,
                content=data,
                content_type=_YAML_MEDIA_TYPE,
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
    ) -> AsyncHarnessEventStream:
        params: Dict[str, Any] = {}
        if replay_from:
            params["replay_from"] = replay_from
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

    async def workspace_upload(
        self,
        session_id: str,
        *,
        path: str,
        data: UploadData,
        is_archive: bool = False,
        content_sha256: Optional[str] = None,
    ) -> Any:
        """Upload raw file (or tar) bytes into a session's sandbox workspace.

        Async counterpart of
        :meth:`pydo.agents.custom_sessions.SessionsOperations.workspace_upload`.
        """
        if not path:
            raise ValueError("path is required")
        content, size, handle = _coerce_upload_content(data)
        try:
            # aiohttp can't reliably stream sync file objects; materialize them.
            if hasattr(content, "read"):
                content = content.read()
                if isinstance(content, str):
                    content = content.encode("utf-8")
                size = len(content)
        finally:
            if handle is not None:
                handle.close()
        if size is not None and size > _MAX_UPLOAD_BYTES:
            raise ValueError(
                f"upload of {size} bytes exceeds the 500 MiB per-request limit"
            )
        headers = {_SHA256_HEADER: content_sha256} if content_sha256 else None
        return await self._parse_json(
            await self._send(
                "POST",
                f"{_BASE_PATH}/{_quote(session_id)}/workspace/upload",
                content=content,
                content_type=_OCTET_STREAM,
                params={"path": path, "is_archive": _bool_param(is_archive)},
                headers=headers,
            ),
        )

    async def workspace_download(
        self,
        session_id: str,
        *,
        path: str,
        as_archive: bool = False,
        require_checksum: bool = False,
    ) -> "AsyncWorkspaceDownload":
        """Download a file (or tar-streamed directory) from a session workspace.

        Async counterpart of
        :meth:`pydo.agents.custom_sessions.SessionsOperations.workspace_download`.
        """
        if not path:
            raise ValueError("path is required")
        request = HttpRequest(
            "GET",
            f"{_BASE_PATH}/{_quote(session_id)}/workspace/download",
            headers={"Accept": _OCTET_STREAM},
            params={"path": path, "as_archive": _bool_param(as_archive)},
        )
        request.url = self._client.format_url(request.url)
        pipeline_response = await self._client._pipeline.run(request, stream=True)
        response = pipeline_response.http_response
        if response.status_code != 200:
            await response.read()
            _raise_agents_http_error(response)
        return AsyncWorkspaceDownload(response, require_checksum=require_checksum)


class AsyncWorkspaceDownload:
    """Async streaming workspace download with best-effort integrity verification.

    Async counterpart of :class:`pydo.agents.custom_sessions.WorkspaceDownload`;
    see that class and :func:`pydo.agents.custom_sessions._verify_download` for
    the verification semantics.
    """

    def __init__(self, response: Any, *, require_checksum: bool = False):
        self._response = response
        self._require_checksum = require_checksum
        self.bytes_read = 0

    @property
    def is_archive(self) -> bool:
        return _download_is_archive(self._response)

    @property
    def size_hint(self) -> Optional[int]:
        return _download_size_hint(self._response)

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[bytes]:
        hasher = hashlib.sha256()
        total = 0
        async for chunk in self._response.iter_bytes():
            if not chunk:
                continue
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            hasher.update(chunk)
            total += len(chunk)
            yield bytes(chunk)
        self.bytes_read = total
        _verify_download(
            self._response, hasher.hexdigest(), total, self._require_checksum
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
        closer = getattr(self._response, "close", None)
        if closer is None:
            return
        try:
            result = closer()
            if hasattr(result, "__await__"):
                await result
        except Exception:  # noqa: BLE001 — best-effort cleanup
            pass

    async def __aenter__(self) -> "AsyncWorkspaceDownload":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


__all__ = [
    "AsyncSessionsOperations",
    "AsyncHarnessEventStream",
    "AsyncWorkspaceDownload",
]
