# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
# pylint: disable=duplicate-code
"""Async Action Gateway API — hand-written; preserved across ``make generate``."""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

from pydo.gateway.custom_models import ToolCall
from pydo.gateway.providers import BaseProvider, default_provider
from pydo.gateway import resolve_gateway_base_url

from .custom_operations import (
    AsyncCodeOperations,
    AsyncGatewayTransport,
    AsyncMCPTransport,
    AsyncRESTTransport,
    AsyncToolsOperations,
    async_execute_tool_calls,
)
from .session import AsyncSession, AsyncSessionsOperations


class AsyncGatewayResources:
    """Async Action Gateway surface attached at ``client.gateway``."""

    def __init__(
        self,
        parent_client: Any,
        *,
        gateway_endpoint: Optional[str] = None,
        provider: Optional[BaseProvider] = None,
        transport: Optional[AsyncGatewayTransport] = None,
    ):
        self._parent = parent_client
        self._gateway_base_url = resolve_gateway_base_url(gateway_endpoint)
        self.provider = provider or default_provider()
        self.sessions = AsyncSessionsOperations(
            parent_client,
            gateway_endpoint=gateway_endpoint,
            provider=self.provider,
        )
        self._transport = transport
        if transport is not None:
            self.tools = AsyncToolsOperations(transport, self.provider)
            self.code = AsyncCodeOperations(transport)
        else:
            self.tools = None
            self.code = None

    @property
    def base_url(self) -> str:
        return self._gateway_base_url

    async def handle_tool_calls(
        self,
        response: Any,
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        if self.tools is None:
            raise RuntimeError(
                "create a session first: session = await client.sessions.create("
                "end_user_id=...); then await session.handle_tool_calls(response)"
            )
        calls = self.provider.extract_tool_calls(response)
        if not calls:
            return []
        results = await async_execute_tool_calls(
            calls, self.tools, rationale=rationale
        )
        return self.provider.format_tool_results(calls, results)

    async def execute_tool_calls(
        self,
        calls: Sequence[ToolCall],
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        if self.tools is None:
            raise RuntimeError(
                "create a session first via await client.sessions.create("
                "end_user_id=...)"
            )
        return await async_execute_tool_calls(calls, self.tools, rationale=rationale)


__all__ = [
    "AsyncGatewayResources",
    "AsyncSession",
    "AsyncSessionsOperations",
    "AsyncGatewayTransport",
    "AsyncMCPTransport",
    "AsyncRESTTransport",
    "AsyncToolsOperations",
    "AsyncCodeOperations",
    "async_execute_tool_calls",
]
