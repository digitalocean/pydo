# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
# pylint: disable=duplicate-code
"""Async Action Gateway sessions."""

from __future__ import annotations

import json as _json
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
    session_mcp_url,
)

from .custom_operations import (
    AsyncCodeOperations,
    AsyncRESTTransport,
    AsyncToolsOperations,
    async_execute_tool_calls,
)

_SESSIONS_PATH = "/v2/sessions"


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
        end_user_id: str,
        name: str,
        policy: Dict[str, Any],
        gateway_base_url: str,
        tools: AsyncToolsOperations,
        code: AsyncCodeOperations,
        provider: BaseProvider,
        raw: Optional[Dict[str, Any]] = None,
    ):
        self.session_urn = session_urn
        self.id = session_urn
        self.end_user_id = end_user_id
        self.name = name
        self.policy = policy
        self._gateway_base_url = gateway_base_url.rstrip("/")
        self.tools = tools
        self.code = code
        self.provider = provider
        self.raw = raw or {}

    @property
    def url(self) -> str:
        return session_mcp_url(self._gateway_base_url, self.session_urn)

    async def handle_tool_calls(
        self,
        response: Any,
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        calls = self.provider.extract_tool_calls(response)
        if not calls:
            return []
        results = await async_execute_tool_calls(
            calls, self.tools, rationale=rationale
        )
        return self.provider.format_tool_results(calls, results)

    async def execute_tool_calls(
        self,
        calls: Sequence[Any],
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        return await async_execute_tool_calls(calls, self.tools, rationale=rationale)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AsyncSession id={self.session_urn!r} "
            f"end_user_id={self.end_user_id!r}>"
        )


class AsyncSessionsOperations:
    """Async create via ``POST /v2/sessions`` on the DO API."""

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
        end_user_id: str,
        *,
        name: Optional[str] = None,
        permissions: Optional[Dict[str, Any]] = None,
    ) -> AsyncSession:
        if not end_user_id or not str(end_user_id).strip():
            raise ValueError("end_user_id is required")

        session_name = name or f"pydo-session-{uuid.uuid4().hex[:8]}"
        policy = normalize_permissions(permissions)
        body = {
            "name": session_name,
            "policy_json": _json.dumps(policy, separators=(",", ":")),
            "end_user_id": str(end_user_id).strip(),
        }

        raw_session = await self._post_create(body)
        session_urn = _pick(raw_session, "sessionUrn", "session_urn")
        if not session_urn:
            raise GatewayProtocolError(
                f"session create response missing sessionUrn: {raw_session!r}"
            )

        transport = AsyncRESTTransport(
            _BaseURLProxy(self._parent._client, self._gateway_base_url),
            session_id=session_urn,
        )
        tools = AsyncToolsOperations(transport, self._provider)
        code = AsyncCodeOperations(transport)
        return AsyncSession(
            session_urn=session_urn,
            end_user_id=_pick(raw_session, "endUserId", "end_user_id")
            or str(end_user_id).strip(),
            name=_pick(raw_session, "name") or session_name,
            policy=policy,
            gateway_base_url=self._gateway_base_url,
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
        if response.status_code not in (200, 201):
            try:
                await response.read()
            except Exception:  # noqa: BLE001
                pass
            _raise_gateway_http_error(response)
        body_bytes = await response.read()
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
        return dict(session)


__all__ = ["AsyncSession", "AsyncSessionsOperations"]
