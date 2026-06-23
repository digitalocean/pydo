# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async Hosted Agents session operations."""
from __future__ import annotations

import json as _json
from typing import Any, AsyncIterator, Dict, List, Optional
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

from pydo.agents.custom_sessions import HarnessStreamError, _raise_agents_http_error, _unwrap_harness_sse_chunk
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
    ) -> Any:
        return await self._parse_json(
            await self._send(
                "GET",
                _BASE_PATH,
                params={
                    "page_token": page_token,
                    "page_size": page_size,
                    "status": status,
                },
            ),
        )

    async def create(
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
        return await self._parse_json(
            await self._send("POST", _BASE_PATH, body=body),
        )

    async def get(self, session_id: str) -> Any:
        return await self._parse_json(
            await self._send("GET", f"{_BASE_PATH}/{_quote(session_id)}"),
        )

    async def destroy(self, session_id: str) -> None:
        await self._send("DELETE", f"{_BASE_PATH}/{_quote(session_id)}")

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


__all__ = ["AsyncSessionsOperations", "AsyncHarnessEventStream"]
