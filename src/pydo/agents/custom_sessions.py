# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Sync Hosted Agents session operations (``/v2/agents/sessions/...``)."""

from __future__ import annotations

import hashlib
import json as _json
import os
import warnings
from typing import Any, BinaryIO, Dict, Iterator, List, Optional, Union
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

from pydo.custom_extensions import SSEStream, _wrap

_ERROR_MAP = {
    401: ClientAuthenticationError,
    404: ResourceNotFoundError,
    409: ResourceExistsError,
    304: ResourceNotModifiedError,
}

_BASE_PATH = "/v2/agents/sessions"

# Private Beta contract: a session is created from an ``agents.yaml`` manifest
# uploaded verbatim. The server routes on this media type (handlers.go:
# isYAMLContentType) and parses the body as the agent spec.
_YAML_MEDIA_TYPE = "application/x-yaml"


def _manifest_bytes(manifest: Union[str, bytes]) -> bytes:
    """Normalize an agents.yaml manifest to non-empty UTF-8 bytes."""
    if isinstance(manifest, str):
        data = manifest.encode("utf-8")
    elif isinstance(manifest, (bytes, bytearray)):
        data = bytes(manifest)
    else:
        raise TypeError("manifest must be a str or bytes YAML document")
    if not data.strip():
        raise ValueError("manifest is empty")
    return data


# Workspace file-transfer contract (custom REST handlers, not grpc-gateway).
_OCTET_STREAM = "application/octet-stream"
_SHA256_HEADER = "X-Content-Sha256"
_IS_ARCHIVE_HEADER = "X-Workspace-Is-Archive"
_SIZE_HINT_HEADER = "X-Workspace-Size-Bytes"
_MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # server returns 413 beyond this

UploadData = Union[bytes, bytearray, str, "os.PathLike[str]", BinaryIO]


class WorkspaceTransferError(RuntimeError):
    """A workspace download failed its integrity check (discard the output)."""


def _bool_param(value: bool) -> str:
    return "true" if value else "false"


def _ci_get(mapping: Any, key: str) -> Optional[str]:
    """Case-insensitive lookup over a header-like mapping."""
    if not mapping:
        return None
    getter = getattr(mapping, "get", None)
    if getter is not None:
        value = getter(key)
        if value is not None:
            return value
    lower = key.lower()
    try:
        items = mapping.items()
    except (AttributeError, TypeError):
        return None
    for name, value in items:
        if isinstance(name, str) and name.lower() == lower:
            return value
    return None


def _extract_trailer(response: Any, name: str) -> Optional[str]:
    """Best-effort read of a chunked-transfer trailer (only valid post-body)."""
    value = _ci_get(getattr(response, "headers", None), name)
    if value:
        return value
    internal = getattr(response, "internal_response", None)
    for obj in (internal, getattr(internal, "raw", None)):
        if obj is None:
            continue
        value = _ci_get(getattr(obj, "trailers", None), name)
        if value:
            return value
    return None


def _download_is_archive(response: Any) -> bool:
    value = _ci_get(getattr(response, "headers", None), _IS_ARCHIVE_HEADER)
    return str(value or "").strip().lower() == "true"


def _download_size_hint(response: Any) -> Optional[int]:
    raw = _ci_get(getattr(response, "headers", None), _SIZE_HINT_HEADER)
    try:
        return int(raw) if raw not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _verify_download(
    response: Any,
    computed_hex: str,
    total_bytes: int,
    require_checksum: bool,
) -> None:
    """Verify a finished download against whatever integrity signal is readable.

    The ``X-Content-Sha256`` trailer is authoritative when readable, but
    CPython's HTTP stack discards chunked trailers, so the check degrades: use
    the trailer if present, else the size hint, else warn (or raise under
    ``require_checksum``).
    """
    expected = _extract_trailer(response, _SHA256_HEADER)
    if expected:
        if expected.strip().lower() != computed_hex.lower():
            raise WorkspaceTransferError(
                "workspace download integrity check failed: SHA-256 mismatch "
                f"(trailer {expected.strip()!r} != computed {computed_hex!r}) — "
                "discard the output."
            )
        return

    size_hint = _download_size_hint(response)
    if size_hint is not None and size_hint != total_bytes:
        raise WorkspaceTransferError(
            "workspace download is truncated: received "
            f"{total_bytes} bytes but the server reported {size_hint} — "
            "discard the output."
        )
    if require_checksum:
        raise WorkspaceTransferError(
            "workspace download integrity check failed: the X-Content-Sha256 "
            "trailer is missing or could not be read. Python's HTTP stack "
            "discards chunked trailers, so strict checksum verification is not "
            "possible on this transport; pass require_checksum=False to accept "
            "downloads (verified by size when the server provides a size hint)."
        )
    warnings.warn(
        "workspace download could not verify the X-Content-Sha256 trailer "
        "(Python's HTTP stack discards chunked trailers); integrity was "
        + (
            "confirmed via the size hint."
            if size_hint is not None
            else "NOT independently verified."
        ),
        stacklevel=2,
    )


def _coerce_upload_content(data: UploadData) -> "tuple[Any, Optional[int], Any]":
    """Normalize an upload payload to ``(content, size_or_None, handle_to_close)``."""
    if isinstance(data, (bytes, bytearray)):
        payload = bytes(data)
        return payload, len(payload), None
    if isinstance(data, (str, os.PathLike)):
        path = os.fspath(data)
        size = os.path.getsize(path)
        handle = open(path, "rb")  # pylint: disable=consider-using-with
        return handle, size, handle
    if hasattr(data, "read"):
        size: Optional[int] = None
        try:
            current = data.tell()
            data.seek(0, os.SEEK_END)
            size = data.tell() - current
            data.seek(current)
        except (OSError, AttributeError, ValueError):
            size = None
        return data, size, None
    raise TypeError(
        "data must be bytes, a filesystem path, or a readable binary stream"
    )


def _unwrap_harness_sse_chunk(chunk: Dict[str, Any]) -> Optional[Any]:
    """Normalize SSE JSON to a harness Event.

    harness-api's HTTP handler emits SPI canonical events
    (``event_id``, ``type``, ``data``).  grpc-gateway streaming uses a
    ``{result, error}`` envelope — accept both.
    """
    if chunk.get("result") is not None:
        return chunk["result"]
    if chunk.get("event_id") and chunk.get("type"):
        return chunk
    return None


def _quote(value: str) -> str:
    return quote(str(value), safe="")


def _response_body_text(response) -> str:
    try:
        if hasattr(response, "read"):
            try:
                response.read()
            except Exception:  # noqa: BLE001
                pass
        body = response.text() if hasattr(response, "text") else response.body()
        if isinstance(body, bytes):
            body = body.decode("utf-8", errors="replace")
        return body or ""
    except Exception:  # noqa: BLE001 — best-effort error detail for callers
        return ""


def _raise_agents_http_error(response) -> None:
    body = _response_body_text(response)
    map_error(
        status_code=response.status_code,
        response=response,
        error_map=_ERROR_MAP,
    )
    message = body.strip() or getattr(response, "reason", None) or "request failed"
    raise HttpResponseError(message=message, response=response)


class HarnessEventStream:
    """Unwraps grpc-gateway SSE envelopes ``{result, error}`` into harness Events."""

    def __init__(self, sse_stream: SSEStream):
        self._sse = sse_stream

    def __iter__(self) -> Iterator[Any]:
        for chunk in self._sse:
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

    def close(self) -> None:
        self._sse.close()

    def __enter__(self) -> "HarnessEventStream":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class HarnessStreamError(RuntimeError):
    """SSE stream error frame from harness-api."""

    def __init__(
        self,
        *,
        grpc_code: Optional[int],
        http_code: Optional[int],
        message: str,
        http_status: Optional[str] = None,
        details: Optional[List[Any]] = None,
    ):
        self.grpc_code = grpc_code
        self.http_code = http_code
        self.http_status = http_status
        self.details = details or []
        super().__init__(message)


class SessionsOperations:
    """Hosted Agents session REST operations."""

    def __init__(self, base_url_proxy):
        self._client = base_url_proxy

    def _send(
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
        pipeline_response = self._client._pipeline.run(request, stream=stream)
        response = pipeline_response.http_response

        if response.status_code not in (200, 204):
            _raise_agents_http_error(response)
        return pipeline_response

    @staticmethod
    def _parse_json(pipeline_response) -> Any:
        response = pipeline_response.http_response
        body = response.text() if hasattr(response, "text") else response.body()
        if not body:
            return None
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        return _wrap(_json.loads(body))

    def list(
        self,
        *,
        page_token: Optional[str] = None,
        page_size: Optional[int] = None,
        status: Optional[str] = None,
    ) -> Any:
        return self._parse_json(
            self._send(
                "GET",
                _BASE_PATH,
                params={
                    "page_token": page_token,
                    "page_size": page_size,
                    "status": status,
                },
            ),
        )

    def create_from_manifest(self, manifest: Union[str, bytes]) -> Any:
        """Create a session from an ``agents.yaml`` manifest.

        This is the supported creation path: the manifest defines everything
        about the session (runtime adapter, sandbox, env vars, egress). It is
        uploaded verbatim as ``application/x-yaml`` and the server owns parsing
        and validation. There are no ``agent_kind``/``repo_hint`` arguments.

        :param manifest: The agent spec as a YAML ``str`` or ``bytes`` document.
        """
        data = _manifest_bytes(manifest)
        return self._parse_json(
            self._send(
                "POST",
                _BASE_PATH,
                content=data,
                content_type=_YAML_MEDIA_TYPE,
            ),
        )

    def get(self, session_id: str) -> Any:
        return self._parse_json(
            self._send("GET", f"{_BASE_PATH}/{_quote(session_id)}"),
        )

    def destroy(self, session_id: str) -> None:
        self._send("DELETE", f"{_BASE_PATH}/{_quote(session_id)}")

    def send_input(self, session_id: str, *, text: str) -> Any:
        return self._parse_json(
            self._send(
                "POST",
                f"{_BASE_PATH}/{_quote(session_id)}/input",
                body={"text": text},
            ),
        )

    def resolve_hitl(
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
        self._send(
            "POST",
            f"{_BASE_PATH}/{_quote(session_id)}/hitl/{_quote(request_id)}",
            body=body,
        )

    def start_oauth_flow(
        self,
        session_id: str,
        provider: str,
        *,
        requested_scopes: Optional[List[str]] = None,
    ) -> Any:
        body: Dict[str, Any] = {}
        if requested_scopes is not None:
            body["requested_scopes"] = list(requested_scopes)
        return self._parse_json(
            self._send(
                "POST",
                f"{_BASE_PATH}/{_quote(session_id)}/oauth/{_quote(provider)}",
                body=body,
            ),
        )

    def stream(
        self,
        session_id: str,
        *,
        replay_from: Optional[str] = None,
        replay_only: bool = False,
    ) -> HarnessEventStream:
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
        pipeline_response = self._client._pipeline.run(request, stream=True)
        response = pipeline_response.http_response
        if response.status_code != 200:
            _raise_agents_http_error(response)
        return HarnessEventStream(SSEStream(response))

    def workspace_upload(
        self,
        session_id: str,
        *,
        path: str,
        data: UploadData,
        is_archive: bool = False,
        content_sha256: Optional[str] = None,
    ) -> Any:
        """Upload raw file (or tar) bytes into a session's sandbox workspace.

        ``POST /v2/agents/sessions/{session_id}/workspace/upload``. ``data`` is
        bytes, a filesystem path, or a readable binary stream. ``is_archive``
        extracts the body as a tar at ``path``; ``content_sha256`` is forwarded
        for the guest to verify. Returns ``{"path": ..., "bytes_written": N}``.
        """
        if not path:
            raise ValueError("path is required")
        content, size, handle = _coerce_upload_content(data)
        try:
            if size is not None and size > _MAX_UPLOAD_BYTES:
                raise ValueError(
                    f"upload of {size} bytes exceeds the 500 MiB per-request limit"
                )
            headers = {_SHA256_HEADER: content_sha256} if content_sha256 else None
            return self._parse_json(
                self._send(
                    "POST",
                    f"{_BASE_PATH}/{_quote(session_id)}/workspace/upload",
                    content=content,
                    content_type=_OCTET_STREAM,
                    params={"path": path, "is_archive": _bool_param(is_archive)},
                    headers=headers,
                ),
            )
        finally:
            if handle is not None:
                handle.close()

    def workspace_download(
        self,
        session_id: str,
        *,
        path: str,
        as_archive: bool = False,
        require_checksum: bool = False,
    ) -> "WorkspaceDownload":
        """Download a file (or tar-streamed directory) from a session workspace.

        ``GET /v2/agents/sessions/{session_id}/workspace/download``. Returns a
        :class:`WorkspaceDownload` that streams and verifies the body.
        ``as_archive`` tar-streams the directory at ``path``. ``require_checksum``
        raises when the SHA-256 trailer cannot be read (default ``False`` since
        CPython's HTTP stack discards chunked trailers).
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
        pipeline_response = self._client._pipeline.run(request, stream=True)
        response = pipeline_response.http_response
        if response.status_code != 200:
            response.read()
            _raise_agents_http_error(response)
        return WorkspaceDownload(response, require_checksum=require_checksum)


class WorkspaceDownload:
    """A streaming workspace download with best-effort integrity verification.

    Iterating yields body chunks while computing the SHA-256; integrity is
    verified once the body is fully consumed (see :func:`_verify_download`).
    Consume it fully (iteration, :meth:`read`, or :meth:`save`) before trusting.
    """

    def __init__(self, response: Any, *, require_checksum: bool = False):
        self._response = response
        self._require_checksum = require_checksum
        self.bytes_read = 0

    @property
    def is_archive(self) -> bool:
        """Whether the response is a tar stream (``X-Workspace-Is-Archive``)."""
        return _download_is_archive(self._response)

    @property
    def size_hint(self) -> Optional[int]:
        """Size hint for progress UIs (``X-Workspace-Size-Bytes``); not framing."""
        return _download_size_hint(self._response)

    def __iter__(self) -> Iterator[bytes]:
        hasher = hashlib.sha256()
        total = 0
        for chunk in self._response.iter_bytes():
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

    def read(self) -> bytes:
        """Consume the whole body and return the (verified) bytes."""
        return b"".join(self)

    def save(self, dest: Union[str, "os.PathLike[str]", BinaryIO]) -> int:
        """Stream the body to *dest* (a path or writable binary file).

        Returns the number of bytes written. If verification fails, a
        file opened from a path is removed before re-raising.
        """
        own = isinstance(dest, (str, os.PathLike))
        handle = open(os.fspath(dest), "wb") if own else dest  # type: ignore[arg-type]
        total = 0
        try:
            for chunk in self:
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

    def close(self) -> None:
        closer = getattr(self._response, "close", None)
        if closer is not None:
            try:
                closer()
            except Exception:  # noqa: BLE001 — best-effort cleanup
                pass

    def __enter__(self) -> "WorkspaceDownload":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


__all__ = [
    "SessionsOperations",
    "HarnessEventStream",
    "HarnessStreamError",
    "WorkspaceDownload",
    "WorkspaceTransferError",
]
