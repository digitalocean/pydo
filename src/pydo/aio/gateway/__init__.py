# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async Action Gateway API — hand-written; preserved across ``make generate``."""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

from pydo.custom_extensions import _BaseURLProxy
from pydo.gateway import resolve_gateway_base_url
from pydo.gateway.custom_models import ToolCall
from pydo.gateway.providers import BaseProvider, default_provider

from .custom_operations import (
    AsyncCodeOperations,
    AsyncGatewayTransport,
    AsyncMCPTransport,
    AsyncToolsOperations,
    async_execute_tool_calls,
)


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
        if transport is None:
            proxy = _BaseURLProxy(
                parent_client._client,
                resolve_gateway_base_url(gateway_endpoint),
            )
            transport = AsyncMCPTransport(proxy)
        self._transport = transport
        self.provider = provider or default_provider()
        self.tools = AsyncToolsOperations(transport, self.provider)
        self.code = AsyncCodeOperations(transport)

    @property
    def base_url(self) -> Optional[str]:
        proxy = getattr(self._transport, "_client", None)
        return getattr(proxy, "_base_url", None)

    async def handle_tool_calls(
        self,
        response: Any,
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        """Async twin of :meth:`pydo.gateway.GatewayResources.handle_tool_calls`."""
        calls = self.provider.extract_tool_calls(response)
        if not calls:
            return []
        results = await async_execute_tool_calls(calls, self.tools, rationale=rationale)
        return self.provider.format_tool_results(calls, results)

    async def execute_tool_calls(
        self,
        calls: Sequence[ToolCall],
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        """Execute pre-extracted :class:`ToolCall` objects; return raw outputs."""
        return await async_execute_tool_calls(calls, self.tools, rationale=rationale)


__all__ = [
    "AsyncGatewayResources",
    "AsyncGatewayTransport",
    "AsyncMCPTransport",
    "AsyncToolsOperations",
    "AsyncCodeOperations",
    "async_execute_tool_calls",
]
