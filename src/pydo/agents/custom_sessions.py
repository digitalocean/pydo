# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Sync Hosted Agents session operations (``/v2/agents/sessions/...``)."""
from __future__ import annotations

import json as _json
from typing import Any, Dict, Iterator, List, Optional
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
        params: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ):
        headers = {"Accept": "application/json"}
        kwargs: Dict[str, Any] = {"headers": headers}
        if params:
            kwargs["params"] = {
                k: v for k, v in params.items() if v is not None and v != ""
            }
        if body is not None:
            headers["Content-Type"] = "application/json"
            kwargs["json"] = body

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

    def create(
        self,
        *,
        agent_kind: str,
        repo_hint: Optional[str] = None,
        idle_timeout_seconds: Optional[int] = None,
    ) -> Any:
        body: Dict[str, Any] = {"agent_kind": agent_kind}
        if repo_hint is not None:
            body["repo_hint"] = repo_hint
        if idle_timeout_seconds is not None:
            body["idle_timeout_seconds"] = idle_timeout_seconds
        return self._parse_json(self._send("POST", _BASE_PATH, body=body))

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


__all__ = ["SessionsOperations", "HarnessEventStream", "HarnessStreamError"]
