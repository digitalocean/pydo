# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Action Gateway entry point: ``from pydo.action_gateway import Client``.

Purpose-built client for the Action Gateway. Create a session first, then
use ``session.tools`` / ``session.code`` / ``session.handle_tool_calls``.
Inference surfaces inherited from :class:`pydo.Client` (``chat``,
``messages``, ``responses``, …) remain available for agentic loops.

Example::

    import os
    from pydo.action_gateway import Client

    client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
    session = client.sessions.create(end_user_id="user-123")

    tools = session.tools()
    response = client.chat.completions.create(
        model="openai-gpt-4o",
        messages=[{"role": "user", "content": "Search for DigitalOcean news"}],
        tools=tools,
    )
    messages = session.handle_tool_calls(response)
"""
from __future__ import annotations

from typing import List, Optional

from pydo import Client as _DigitalOceanClient
from pydo._patch import TokenCredentials
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
    Session,
    SessionsOperations,
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
    """Action Gateway–focused DigitalOcean Python client.

    Primary surface:

    * ``client.sessions.create(end_user_id=...)`` → :class:`Session`
    * ``session.tools`` / ``session.tools()`` — discover and wrap tools
    * ``session.code`` — sandboxed Python execution
    * ``session.handle_tool_calls(response)`` — run model tool calls
    * ``session.url`` — MCP URL for external clients

    Inherits the full :class:`pydo.Client` machinery (auth, transport,
    inference routing), so agentic loops can call ``client.chat`` /
    ``client.messages`` on the same instance.
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
                "ensure pydo.gateway is installed"
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
        return "<pydo.action_gateway.Client>"


__all__ = [
    "Client",
    "TokenCredentials",
    "Session",
    "SessionsOperations",
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
