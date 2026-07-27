# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
# pylint: disable=duplicate-code
"""Async Action Gateway sessions."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Sequence

from azure.core.rest import HttpRequest

from pydo.custom_extensions import _BaseURLProxy
from pydo.gateway.custom_models import GatewayProtocolError
from pydo.gateway.providers import BaseProvider, default_provider
from pydo.gateway.session import normalize_permissions
from pydo.gateway.transport import (
    _parse_json_body,
    _raise_gateway_http_error,
    resolve_gateway_base_url,
)

from .custom_operations import (
    AsyncCodeOperations,
    AsyncMCPTransport,
    AsyncToolsOperations,
    async_execute_tool_calls,
)

_SESSIONS_PATH = "/v2/action-gateway/sessions"


def _pick(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


class AsyncSession:
    """Async twin of :class:`pydo.gateway.session.Session`."""

    def __init__(
        self,
        *,
        session_urn: str,
        actor_id: str,
        name: str,
        policy: Dict[str, Any],
        mcp_url: str,
        tools: AsyncToolsOperations,
        code: AsyncCodeOperations,
        provider: BaseProvider,
        raw: Optional[Dict[str, Any]] = None,
    ):
        self.session_urn = session_urn
        self.id = session_urn
        self.actor_id = actor_id
        self.name = name
        self.policy = policy
        self._mcp_url = mcp_url
        self.tools = tools
        self.code = code
        self.provider = provider
        self.raw = raw or {}

    @property
    def url(self) -> str:
        return self._mcp_url

    async def handle_tool_calls(
        self,
        response: Any,
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        calls = self.provider.extract_tool_calls(response)
        if not calls:
            return []
        results = await async_execute_tool_calls(calls, self.tools, rationale=rationale)
        return self.provider.format_tool_results(calls, results)

    async def execute_tool_calls(
        self,
        calls: Sequence[Any],
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        return await async_execute_tool_calls(calls, self.tools, rationale=rationale)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AsyncSession id={self.session_urn!r} " f"actor_id={self.actor_id!r}>"


class AsyncSessionsOperations:
    """Async create via ``POST /v2/action-gateway/sessions`` on the DO API."""

    def __init__(
        self,
        parent_client: Any,
        *,
        gateway_endpoint: Optional[str] = None,
        provider: Optional[BaseProvider] = None,
    ):
        self._parent = parent_client
        self._gateway_base_url = resolve_gateway_base_url(gateway_endpoint)
        self._provider = provider or default_provider()

    async def create(
        self,
        actor_id: str,
        *,
        name: Optional[str] = None,
        permissions: Optional[Dict[str, Any]] = None,
    ) -> AsyncSession:
        if not actor_id or not str(actor_id).strip():
            raise ValueError("actor_id is required")

        session_name = name or f"pydo-session-{uuid.uuid4().hex[:8]}"
        policy = normalize_permissions(permissions)
        body = {
            "name": session_name,
            "policy": policy,
            "actor_id": str(actor_id).strip(),
        }

        raw_session = await self._post_create(body)
        session_urn = _pick(raw_session, "sessionUrn", "session_urn")
        if not session_urn:
            raise GatewayProtocolError(
                f"session create response missing sessionUrn: {raw_session!r}"
            )

        mcp_url = _pick(raw_session, "mcpUrl", "mcp_url")
        if not mcp_url:
            raise GatewayProtocolError(
                f"session create response missing mcpUrl: {raw_session!r}"
            )

        transport = AsyncMCPTransport(
            _BaseURLProxy(self._parent._client, self._gateway_base_url),
            session_id=session_urn,
            actor_id=actor_id,
            endpoint_url=mcp_url,
        )
        tools = AsyncToolsOperations(transport, self._provider)
        code = AsyncCodeOperations(transport)
        return AsyncSession(
            session_urn=session_urn,
            actor_id=str(actor_id).strip(),
            name=_pick(raw_session, "name") or session_name,
            policy=policy,
            mcp_url=mcp_url,
            tools=tools,
            code=code,
            provider=self._provider,
            raw=raw_session,
        )

    async def _post_create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        client = self._parent._client
        request = HttpRequest(
            "POST",
            _SESSIONS_PATH,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=body,
        )
        request.url = client.format_url(request.url)
        pipeline_response = await client._pipeline.run(request)
        response = pipeline_response.http_response
        body_bytes = await response.read()
        if response.status_code not in (200, 201):
            _raise_gateway_http_error(response)
        payload = _parse_json_body(body_bytes)
        if not isinstance(payload, dict):
            raise GatewayProtocolError(
                f"unexpected session create response: {payload!r}"
            )
        session = payload.get("session")
        if not isinstance(session, dict):
            raise GatewayProtocolError(
                f"session create response missing session object: {payload!r}"
            )
        result = dict(session)
        mcp_url = _pick(payload, "mcpUrl", "mcp_url")
        if mcp_url:
            result["mcpUrl"] = mcp_url
        return result


__all__ = ["AsyncSession", "AsyncSessionsOperations"]
