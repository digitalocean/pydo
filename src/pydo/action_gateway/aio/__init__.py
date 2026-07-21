# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
# pylint: disable=duplicate-code
"""Async Action Gateway entry point: ``from pydo.action_gateway.aio import Client``.

Asynchronous twin of :class:`pydo.action_gateway.Client`. Same surface,
``await``-friendly. See :mod:`pydo.action_gateway` for usage details.
"""
from __future__ import annotations

from typing import List, Optional

from pydo.aio import Client as _DigitalOceanClient
from pydo.aio._patch import TokenCredentials
from pydo.aio.gateway import AsyncSession, AsyncSessionsOperations
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
    ToolCall,
    normalize_permissions,
    resolve_gateway_base_url,
    session_mcp_url,
)

_GATEWAY_SURFACE: tuple = (
    "base_url",
    "chat",
    "messages",
    "provider",
    "responses",
    "sessions",
)


class Client(_DigitalOceanClient):
    """Action Gateway–focused DigitalOcean async client.

    Asynchronous counterpart to :class:`pydo.action_gateway.Client`.
    Create a session with ``await client.sessions.create(end_user_id=...)``,
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
        self.sessions = gateway.sessions
        self.provider = gateway.provider

    @property
    def base_url(self) -> Optional[str]:
        """Resolved Action Gateway base URL."""
        gateway = self.gateway
        return gateway.base_url if gateway is not None else None

    def __dir__(self) -> List[str]:
        return sorted(set(_GATEWAY_SURFACE))

    def __repr__(self) -> str:
        return "<pydo.action_gateway.aio.Client>"


__all__ = [
    "Client",
    "TokenCredentials",
    "AsyncSession",
    "AsyncSessionsOperations",
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
