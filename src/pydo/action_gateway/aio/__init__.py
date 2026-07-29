# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
# pylint: disable=duplicate-code
"""Async Action Gateway entry point: ``ActionGatewayClient``.

Asynchronous twin of :class:`pydo.action_gateway.Client`. Same surface,
``await``-friendly. See :mod:`pydo.action_gateway` for usage details.
"""
from __future__ import annotations

from typing import List, Optional

from pydo.aio import Client as _DigitalOceanClient
from pydo.aio._patch import TokenCredentials
from pydo.aio.gateway import (
    AsyncSession,
    AsyncSessionsOperations,
)
from pydo.gateway import (
    META_CODE,
    META_INVOKE,
    META_SEARCH,
    META_TOOL_NAMES,
    DEFAULT_GATEWAY_BASE_URL,
    ChatCompletionsProvider,
    GatewayProtocolError,
    GatewayToolError,
    MessagesProvider,
    ResponsesProvider,
    Toolbelt,
    ToolCall,
    normalize_permissions,
    resolve_gateway_base_url,
    session_mcp_url,
)

_GATEWAY_SURFACE: tuple = (
    "base_url",
    "chat",
    "create_toolbelt",
    "messages",
    "provider",
    "responses",
    "session",
    "sessions",
    "sessions_api",
    "connections",
    "tools",
    "toolbelts",
    "users",
)


class Client(_DigitalOceanClient):
    """Action Gateway–focused DigitalOcean async client.

    Asynchronous counterpart to :class:`pydo.action_gateway.Client`.
    Create a session with ``await client.session.create(actor_id=...)``,
    then use ``session.tools`` / ``session.code`` /
    ``await session.handle_tool_calls(...)``.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        api_key: Optional[str] = None,
        timeout: int = 120,
        gateway_endpoint: Optional[str] = None,
        gateway_provider=None,
        **kwargs,
    ) -> None:
        super().__init__(
            token=token,
            api_key=api_key,
            timeout=timeout,
            gateway_endpoint=gateway_endpoint,
            gateway_provider=gateway_provider,
            **kwargs,
        )
        gateway = self.gateway
        if gateway is None:
            raise RuntimeError(
                "Action Gateway package is unavailable; "
                "ensure pydo.aio.gateway is installed"
            )
        self.sessions_api = self.sessions
        self.sessions = gateway.sessions
        self.session = self.sessions
        self.provider = gateway.provider

    async def create_toolbelt(self, name: str, tools, **kwargs) -> Toolbelt:
        """Create a versioned collection of Action Gateway tools."""
        if isinstance(tools, (str, bytes)):
            raise TypeError("tools must be an iterable of tool names")
        body = {"name": name, "tools": list(tools), **kwargs}
        response = await self.toolbelts.create(body=body)
        return Toolbelt(response["toolbelt"])

    @property
    def base_url(self) -> Optional[str]:
        """Resolved Action Gateway base URL."""
        gateway = self.gateway
        return gateway.base_url if gateway is not None else None

    def __dir__(self) -> List[str]:
        return sorted(set(_GATEWAY_SURFACE))

    def __repr__(self) -> str:
        return "<pydo.action_gateway.aio.Client>"


ActionGatewayClient = Client


__all__ = [
    "Client",
    "ActionGatewayClient",
    "TokenCredentials",
    "AsyncSession",
    "AsyncSessionsOperations",
    "Toolbelt",
    "ChatCompletionsProvider",
    "MessagesProvider",
    "ResponsesProvider",
    "GatewayToolError",
    "GatewayProtocolError",
    "ToolCall",
    "normalize_permissions",
    "session_mcp_url",
    "META_SEARCH",
    "META_INVOKE",
    "META_CODE",
    "META_TOOL_NAMES",
    "DEFAULT_GATEWAY_BASE_URL",
    "resolve_gateway_base_url",
]
