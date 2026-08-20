# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Sync Hosted Agents session operations (``/v2/agents/sessions/...``)."""

from __future__ import annotations

import hashlib
import json as _json
import os
import time
import warnings
from typing import Any, BinaryIO, Dict, Iterator, List, NamedTuple, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

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
_OK_STATUS = (200, 201, 202, 204)

# CreateSession often blocks until the sandbox is READY (Firecracker boot).
# doctl tolerates several minutes; azure-core's default absolute timeout is ~120s
# and surfaces as ServiceResponseTimeoutError.
_DEFAULT_CREATE_TIMEOUT = 600.0
_DEFAULT_REQUEST_TIMEOUT = 120.0

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


# Staged workspace transfers (``.../workspace/transfers``). Prefer these over
# the older streaming upload/download routes for all payload sizes.
_OCTET_STREAM = "application/octet-stream"
_TRANSFERS_SUFFIX = "workspace/transfers"
_MAX_TRANSFER_BYTES = 50 * 1024 * 1024 * 1024  # 50 GiB
_DEFAULT_POLL_INTERVAL = 1.0
_DEFAULT_POLL_TIMEOUT = 600.0
_DOWNLOAD_CHUNK = 1024 * 1024

UploadData = Union[bytes, bytearray, str, "os.PathLike[str]", BinaryIO]


class WorkspaceTransferError(RuntimeError):
    """A workspace transfer failed (integrity check, timeout, or server error)."""


def _field(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    getter = getattr(obj, "get", None)
    if getter is not None:
        return getter(key, default)
    return getattr(obj, key, default)


def _coerce_upload_content(data: UploadData) -> "tuple[Any, int, Any]":
    """Normalize an upload payload to ``(content, size, handle_to_close)``.

    Size is required by the staged transfer API.
    """
    if isinstance(data, (bytes, bytearray)):
        payload = bytes(data)
        return payload, len(payload), None
    if isinstance(data, (str, os.PathLike)):
        path = os.fspath(data)
        size = os.path.getsize(path)
        handle = open(path, "rb")  # pylint: disable=consider-using-with
        return handle, size, handle
    if hasattr(data, "read"):
        try:
            current = data.tell()
            data.seek(0, os.SEEK_END)
            size = data.tell() - current
            data.seek(current)
        except (OSError, AttributeError, ValueError) as exc:
            raise ValueError(
                "upload streams must support seek/tell so size_bytes can be "
                "determined; pass bytes or a filesystem path instead"
            ) from exc
        return data, int(size), None
    raise TypeError(
        "data must be bytes, a filesystem path, or a readable binary stream"
    )


def _read_exact(source: Any, size: int) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        raise TypeError("use slicing for bytes payloads")
    chunks: List[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = source.read(remaining)
        if not chunk:
            raise WorkspaceTransferError(
                f"unexpected EOF while reading upload part "
                f"({size - remaining} of {size} bytes read)"
            )
        if isinstance(chunk, str):
            chunk = chunk.encode("utf-8")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _http_put_bytes(url: str, data: bytes) -> None:
    """PUT part bytes to a presigned Spaces URL (not via OHS)."""
    request = Request(
        url,
        data=data,
        method="PUT",
        headers={"Content-Type": _OCTET_STREAM},
    )
    try:
        with urlopen(request) as resp:  # noqa: S310 — caller-supplied Spaces URL
            body = resp.read()
            status = getattr(resp, "status", None) or resp.getcode()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise WorkspaceTransferError(
            f"part upload failed: HTTP {exc.code}"
            + (f": {detail.strip()}" if detail.strip() else "")
        ) from exc
    except URLError as exc:
        raise WorkspaceTransferError(f"part upload failed: {exc.reason}") from exc
    if status not in (200, 201, 204):
        raise WorkspaceTransferError(
            f"part upload failed: HTTP {status}"
            + (f": {body[:200]!r}" if body else "")
        )


def _http_get_iter(url: str) -> Iterator[bytes]:
    """Stream bytes from a presigned download URL (not via OHS)."""
    request = Request(url, method="GET")
    try:
        resp = urlopen(request)  # noqa: S310 — caller-supplied Spaces URL
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise WorkspaceTransferError(
            f"download failed: HTTP {exc.code}"
            + (f": {detail.strip()}" if detail.strip() else "")
        ) from exc
    except URLError as exc:
        raise WorkspaceTransferError(f"download failed: {exc.reason}") from exc
    try:
        status = getattr(resp, "status", None) or resp.getcode()
        if status != 200:
            raise WorkspaceTransferError(f"download failed: HTTP {status}")
        while True:
            chunk = resp.read(_DOWNLOAD_CHUNK)
            if not chunk:
                break
            yield chunk
    finally:
        try:
            resp.close()
        except Exception:  # noqa: BLE001
            pass


def _verify_transfer_sha256(
    computed_hex: str,
    expected: Optional[str],
    *,
    total_bytes: int,
    size_hint: Optional[int],
    require_checksum: bool,
) -> None:
    if expected:
        if expected.strip().lower() != computed_hex.lower():
            raise WorkspaceTransferError(
                "workspace download integrity check failed: SHA-256 mismatch "
                f"(expected {expected.strip()!r} != computed {computed_hex!r}) — "
                "discard the output."
            )
        return
    if size_hint is not None and size_hint != total_bytes:
        raise WorkspaceTransferError(
            "workspace download is truncated: received "
            f"{total_bytes} bytes but the server reported {size_hint} — "
            "discard the output."
        )
    if require_checksum:
        raise WorkspaceTransferError(
            "workspace download integrity check failed: sha256 was missing "
            "from the completed transfer response."
        )
    warnings.warn(
        "workspace download completed without a sha256 digest; integrity was "
        + (
            "confirmed via bytes_written."
            if size_hint is not None
            else "NOT independently verified."
        ),
        stacklevel=2,
    )


_DROPPED_TENANT_FIELDS = ("tenant_id", "team_id")


def _strip_tenant_fields(obj: Any) -> Any:
    """Recursively remove tenant/team identifiers from a parsed response.

    Neither identifier is part of the client-facing contract for hosted-agent
    sessions or events: the tenant is implied by the credential the request
    was made with. This walks nested dicts/lists so it strips consistently
    whether it runs on a single SSE event or a whole ``{"sessions": [...]}``
    GET/LIST response body.
    """
    if isinstance(obj, dict):
        for key in _DROPPED_TENANT_FIELDS:
            obj.pop(key, None)
        for value in obj.values():
            _strip_tenant_fields(value)
    elif isinstance(obj, list):
        for item in obj:
            _strip_tenant_fields(item)
    return obj


def _unwrap_harness_sse_chunk(chunk: Dict[str, Any]) -> Optional[Any]:
    """Normalize SSE JSON to a harness Event.

    harness-api's HTTP handler emits SPI canonical events
    (``event_id``, ``type``, ``data``).  grpc-gateway streaming uses a
    ``{result, error}`` envelope — accept both.  Either shape may still carry
    a tenant/team identifier, which is dropped before the event is yielded.
    """
    if chunk.get("result") is not None:
        return _strip_tenant_fields(chunk["result"])
    if chunk.get("event_id") and chunk.get("type"):
        return _strip_tenant_fields(chunk)
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


class HistoryPage(NamedTuple):
    """One backward page of session history.

    ``next_before`` is the cursor to pass as ``before`` for the page before
    this one; it is ``None`` when the page came back empty.
    """

    events: List[Any]
    has_more: Optional[bool]
    next_before: Optional[str]


class HarnessEventStream:
    """Unwraps grpc-gateway SSE envelopes ``{result, error}`` into harness Events."""

    def __init__(self, sse_stream: SSEStream):
        self._sse = sse_stream
        self.oldest_event_id: Optional[str] = None

    @property
    def has_more(self) -> Optional[bool]:
        """Whether older history remains, per the server's trailing comment.

        Only history pages (``before=``) carry this; ``None`` until the
        ``: has_more=...`` frame arrives, so read it after iterating.
        """
        return getattr(self._sse, "has_more", None)

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
                if self.oldest_event_id is None:
                    event_id = _field(event, "event_id")
                    if event_id:
                        self.oldest_event_id = str(event_id)
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
            # azure-core: connection_timeout + read_timeout; also raise the
            # retry policy's absolute deadline so long CreateSession calls
            # are not aborted mid-provision.
            run_kwargs["connection_timeout"] = float(timeout)
            run_kwargs["read_timeout"] = float(timeout)
            run_kwargs["timeout"] = float(timeout)
        pipeline_response = self._client._pipeline.run(request, **run_kwargs)
        response = pipeline_response.http_response

        if response.status_code not in _OK_STATUS:
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
        return _strip_tenant_fields(_wrap(_json.loads(body)))

    def list(
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
        return self._parse_json(
            self._send(
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

    def create_from_manifest(
        self,
        manifest: Union[str, bytes],
        *,
        openai_session_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Create a session from an ``agents.yaml`` manifest.

        This is the supported creation path: the manifest defines everything
        about the session (runtime adapter, sandbox, env vars, egress). It is
        uploaded verbatim as ``application/x-yaml`` and the server owns parsing
        and validation. There are no ``agent_kind``/``repo_hint`` arguments.

        For OpenAI sandbox-provider sessions (``AGENT_KIND_OPENAI_CODEX``),
        pass ``openai_session_id`` (the ``sess_…`` from OpenAI's create-session
        call). The server persists it for attach correlation; doctl /
        :meth:`pydo.agents.AgentsResources.start` resolve ``${ENV_ID}`` /
        ``${OPENAI_API_KEY}`` client-side before calling this method.

        :param manifest: The agent spec as a YAML ``str`` or ``bytes`` document.
        :param openai_session_id: Optional OpenAI session id query param.
        :param timeout: HTTP timeout in seconds (defaults to 600 for create —
            sandbox boot can exceed the client-wide 120s default).
        """
        data = _manifest_bytes(manifest)
        params: Optional[Dict[str, Any]] = None
        if openai_session_id:
            params = {"openai_session_id": openai_session_id}
        return self._parse_json(
            self._send(
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

    def create_from_config(
        self,
        *,
        name: str,
        config_id: str,
        timeout: Optional[float] = None,
    ) -> Any:
        """Create a session from a durable Agent Config (``POST /v2/agents/sessions``).

        Sends ``application/json`` with ``name`` and ``config_id``. The server
        loads the config, resolves credentials from Secrets Manager, and
        provisions the sandbox. No inline secrets are accepted.
        """
        if not name or not config_id:
            raise ValueError("name and config_id are required")
        return self._parse_json(
            self._send(
                "POST",
                _BASE_PATH,
                body={"name": name, "config_id": config_id},
                timeout=(
                    _DEFAULT_CREATE_TIMEOUT if timeout is None else float(timeout)
                ),
            ),
        )

    def get(self, session_id: str) -> Any:
        return self._parse_json(
            self._send("GET", f"{_BASE_PATH}/{_quote(session_id)}"),
        )

    def destroy(self, session_id: str) -> None:
        self._send("DELETE", f"{_BASE_PATH}/{_quote(session_id)}")

    def pause(self, session_id: str) -> Any:
        """Pause a running session (``POST .../{session_id}/pause``)."""
        return self._parse_json(
            self._send("POST", f"{_BASE_PATH}/{_quote(session_id)}/pause"),
        )

    def resume(self, session_id: str) -> Any:
        """Resume a paused session (``POST .../{session_id}/resume``)."""
        return self._parse_json(
            self._send("POST", f"{_BASE_PATH}/{_quote(session_id)}/resume"),
        )

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

    def start_provider_auth(self, provider: str) -> Any:
        """Start (or resume) the team-scoped connect flow for an external
        provider (e.g. GitHub).

        The team is derived from the API token; there is no session and no
        request body. Returns the parsed JSON: ``status`` ("pending" or
        "success") and, while pending, ``connect_url`` / ``poll_url`` /
        ``verification_code`` for the browser authorization step. The
        authorization handle is never exposed — tokens are exchanged
        server-side at session time.
        """
        return self._parse_json(
            self._send(
                "POST",
                f"/v2/agents/auth/{_quote(provider)}",
                body={},
            ),
        )

    def poll_provider_auth(self, provider: str, poll_url: str) -> Any:
        """Check whether a pending connect link has been authorized.

        ``poll_url`` is the value returned by :meth:`start_provider_auth`.
        Returns the parsed JSON with ``status`` ("pending" or "success").
        """
        if not poll_url:
            raise ValueError("poll_url is required")
        return self._parse_json(
            self._send(
                "GET",
                f"/v2/agents/auth/{_quote(provider)}/poll",
                params={"poll_url": poll_url},
            ),
        )

    def stream(
        self,
        session_id: str,
        *,
        replay_from: Optional[str] = None,
        replay_only: bool = False,
        before: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> HarnessEventStream:
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
        pipeline_response = self._client._pipeline.run(request, stream=True)
        response = pipeline_response.http_response
        if response.status_code != 200:
            _raise_agents_http_error(response)
        return HarnessEventStream(SSEStream(response))

    def history_page(
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
                page = sessions.history_page(session_id, before=cursor)
                older = page.events + older
                cursor = page.next_before if page.has_more else None
        """
        if not before:
            raise ValueError("before is required")
        stream = self.stream(session_id, before=before, limit=limit)
        with stream:
            events = list(stream)
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

    def create_transfer(
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
        """Start a staged workspace transfer (``POST .../workspace/transfers``).

        ``direction`` is ``"upload"`` or ``"download"``. Upload responses are
        ``201`` and include ``part_size``; download responses are ``202``.
        """
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
        return self._parse_json(
            self._send("POST", self._transfers_path(session_id), body=body),
        )

    def create_part_upload_urls(
        self,
        session_id: str,
        transfer_id: str,
        *,
        part_numbers: List[int],
    ) -> Any:
        """Get presigned URLs for one or more upload parts (upload only).

        Request body is ``{"part_numbers": [1, 2, ...]}``. The response includes
        ``part_urls``: ``[{"part_number": N, "upload_url": "..."}, ...]``.
        """
        numbers = [int(n) for n in part_numbers]
        if not numbers or any(n < 1 for n in numbers):
            raise ValueError("part_numbers must be a non-empty list of integers >= 1")
        return self._parse_json(
            self._send(
                "POST",
                self._transfers_path(session_id, transfer_id, "part-upload-urls"),
                body={"part_numbers": numbers},
            ),
        )

    def create_part_upload_url(
        self,
        session_id: str,
        transfer_id: str,
        *,
        part_number: int,
    ) -> Any:
        """Convenience wrapper: request a single part URL via the batch endpoint.

        Returns the matching ``part_urls`` entry (``part_number`` + ``upload_url``).
        """
        resp = self.create_part_upload_urls(
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

    def commit_upload(
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
        return self._parse_json(
            self._send(
                "POST",
                self._transfers_path(session_id, transfer_id, "commit"),
                body=body,
            ),
        )

    def get_transfer(self, session_id: str, transfer_id: str) -> Any:
        """Poll transfer status; downloads expose ``download_url`` + ``sha256``."""
        return self._parse_json(
            self._send("GET", self._transfers_path(session_id, transfer_id)),
        )

    def cancel_transfer(
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
        return self._parse_json(
            self._send(
                "POST",
                self._transfers_path(session_id, transfer_id, "cancel"),
                body=body,
            ),
        )

    def wait_transfer(
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
            info = self.get_transfer(session_id, transfer_id)
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
            time.sleep(max(poll_interval, 0.05))

    def workspace_upload(
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
        """Upload a file/tar into the workspace via staged transfers.

        Uses ``CreateTransfer`` → part PUTs to Spaces → ``CommitUpload`` →
        poll ``GetTransfer`` for all sizes (up to 50 GiB). ``data`` is bytes, a
        filesystem path, or a seekable binary stream. Returns the completed
        transfer record (includes ``bytes_written`` / ``sha256`` when present).
        """
        if not path:
            raise ValueError("path is required")
        content, size, handle = _coerce_upload_content(data)
        try:
            if size > _MAX_TRANSFER_BYTES:
                raise ValueError(
                    f"upload of {size} bytes exceeds the 50 GiB transfer limit"
                )
            created = self.create_transfer(
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
                raise WorkspaceTransferError("CreateTransfer response missing transfer_id")
            if part_size < 1:
                raise WorkspaceTransferError(
                    "CreateTransfer response missing a positive part_size"
                )

            hasher = hashlib.sha256()
            if size == 0:
                # Still need at least one empty part URL? Skip parts; commit only.
                part_url_by_number: Dict[int, str] = {}
            else:
                num_parts = (size + part_size - 1) // part_size
                part_numbers = list(range(1, num_parts + 1))
                batch = self.create_part_upload_urls(
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
                if isinstance(content, (bytes, bytearray)):
                    chunk = bytes(content[offset : offset + length])
                else:
                    chunk = _read_exact(content, length)
                hasher.update(chunk)
                upload_url = part_url_by_number[part_number]
                _http_put_bytes(upload_url, chunk)
                offset += length
                part_number += 1

            digest = content_sha256 or hasher.hexdigest()
            self.commit_upload(session_id, transfer_id, sha256=digest)
            completed = self.wait_transfer(
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
            # Best-effort cancel if we already created a transfer.
            transfer_id = locals().get("transfer_id")
            if transfer_id:
                try:
                    self.cancel_transfer(session_id, transfer_id, reason="client_error")
                except Exception:  # noqa: BLE001
                    pass
            raise
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
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
        timeout: float = _DEFAULT_POLL_TIMEOUT,
    ) -> "WorkspaceDownload":
        """Download a workspace file/tar via staged transfers.

        Uses ``CreateTransfer`` (download) → poll ``GetTransfer`` → GET the
        presigned ``download_url``, verifying ``sha256`` from the JSON status.
        """
        if not path:
            raise ValueError("path is required")
        created = self.create_transfer(
            session_id,
            direction="download",
            path=path,
            as_archive=as_archive,
        )
        transfer_id = _field(created, "transfer_id")
        if not transfer_id:
            raise WorkspaceTransferError("CreateTransfer response missing transfer_id")
        try:
            completed = self.wait_transfer(
                session_id,
                transfer_id,
                poll_interval=poll_interval,
                timeout=timeout,
            )
        except Exception:
            try:
                self.cancel_transfer(session_id, transfer_id, reason="client_error")
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
        return WorkspaceDownload(
            download_url=str(download_url),
            expected_sha256=_field(completed, "sha256"),
            size_hint=size_hint,
            is_archive=as_archive,
            require_checksum=require_checksum,
            transfer_id=str(transfer_id),
        )


class WorkspaceDownload:
    """Streaming download from a completed staged transfer's ``download_url``.

    Iterating yields body chunks while computing SHA-256; integrity is verified
    against the digest from :meth:`SessionsOperations.get_transfer` once the
    body is fully consumed. Consume fully (iteration, :meth:`read`, or
    :meth:`save`) before trusting the output.
    """

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
        """Whether the caller requested a tar archive download."""
        return self._is_archive

    @property
    def size_hint(self) -> Optional[int]:
        """``bytes_written`` from the completed transfer, when known."""
        return self._size_hint

    @property
    def expected_sha256(self) -> Optional[str]:
        """SHA-256 from the completed transfer response (verify after download)."""
        return self._expected_sha256

    def __iter__(self) -> Iterator[bytes]:
        hasher = hashlib.sha256()
        total = 0
        for chunk in _http_get_iter(self._download_url):
            hasher.update(chunk)
            total += len(chunk)
            yield chunk
        self.bytes_read = total
        _verify_transfer_sha256(
            hasher.hexdigest(),
            self._expected_sha256,
            total_bytes=total,
            size_hint=self._size_hint,
            require_checksum=self._require_checksum,
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
        return None

    def __enter__(self) -> "WorkspaceDownload":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


__all__ = [
    "SessionsOperations",
    "HarnessEventStream",
    "HarnessStreamError",
    "HistoryPage",
    "WorkspaceDownload",
    "WorkspaceTransferError",
    "UploadData",
]
