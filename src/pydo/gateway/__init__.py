# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Action Gateway API — hand-written; preserved across ``make generate``.

Session-first surface: create a session on the DigitalOcean API
(``POST /v2/sessions``), then discover/invoke tools and run code over the
gateway REST endpoints with ``X-Session-Id``. Composio-style providers make
session tools plug into pydo inference surfaces (chat completions, messages,
responses).
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

from .custom_models import (
    META_CODE,
    META_INVOKE,
    META_SEARCH,
    META_TOOL_NAMES,
    GatewayProtocolError,
    GatewayToolError,
    RecoveryHint,
    ToolCall,
    ToolErrorClass,
    ToolResultStatus,
)
from .custom_operations import CodeOperations, ToolsOperations, normalize_invoke_arguments
from .providers import (
    BaseProvider,
    ChatCompletionsProvider,
    MessagesProvider,
    ResponsesProvider,
    default_provider,
    execute_tool_calls,
    simplify_inference_tool_schema,
    simplify_messages_input_schema,
)
from .session import (
    Session,
    SessionsOperations,
    normalize_permissions,
    serialize_policy_json,
)
from .transport import (
    MCP_PROTOCOL_VERSION,
    SESSION_ID_HEADER,
    DEFAULT_GATEWAY_BASE_URL,
    GatewayTransport,
    MCPTransport,
    RESTTransport,
    resolve_gateway_base_url,
    session_mcp_url,
)

_ENV_VAR = "PYDO_GATEWAY_ENDPOINT"  # kept for docs / discoverability


class GatewayResources:
    """Action Gateway surface attached at ``client.gateway``.

    Primary entry point is :attr:`sessions` — create a :class:`Session` before
    invoking tools. Legacy ``tools`` / ``code`` attributes require an explicit
    session-bound transport and are not usable until a session exists.
    """

    def __init__(
        self,
        parent_client: Any,
        *,
        gateway_endpoint: Optional[str] = None,
        provider: Optional[BaseProvider] = None,
        transport: Optional[GatewayTransport] = None,
    ):
        self._parent = parent_client
        self._gateway_endpoint = gateway_endpoint
        self._gateway_base_url = resolve_gateway_base_url(gateway_endpoint)
        self.provider = provider or default_provider()
        self.sessions = SessionsOperations(
            parent_client,
            gateway_endpoint=gateway_endpoint,
            provider=self.provider,
        )
        # Optional pre-bound transport (tests). Production callers use sessions.
        self._transport = transport
        if transport is not None:
            self.tools = ToolsOperations(transport, self.provider)
            self.code = CodeOperations(transport)
        else:
            self.tools = None
            self.code = None

    @property
    def base_url(self) -> str:
        return self._gateway_base_url

    def handle_tool_calls(
        self,
        response: Any,
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        """Deprecated path — prefer ``session.handle_tool_calls(response)``."""
        if self.tools is None:
            raise RuntimeError(
                "create a session first: session = client.sessions.create("
                "end_user_id=...); then session.handle_tool_calls(response)"
            )
        calls = self.provider.extract_tool_calls(response)
        if not calls:
            return []
        results = execute_tool_calls(calls, self.tools, rationale=rationale)
        return self.provider.format_tool_results(calls, results)

    def execute_tool_calls(
        self,
        calls: Sequence[ToolCall],
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        if self.tools is None:
            raise RuntimeError(
                "create a session first via client.sessions.create(end_user_id=...)"
            )
        return execute_tool_calls(calls, self.tools, rationale=rationale)


__all__ = [
    "GatewayResources",
    "Session",
    "SessionsOperations",
    "normalize_permissions",
    "serialize_policy_json",
    "ToolsOperations",
    "CodeOperations",
    "normalize_invoke_arguments",
    "GatewayTransport",
    "RESTTransport",
    "MCPTransport",
    "MCP_PROTOCOL_VERSION",
    "SESSION_ID_HEADER",
    "session_mcp_url",
    "BaseProvider",
    "ChatCompletionsProvider",
    "MessagesProvider",
    "ResponsesProvider",
    "default_provider",
    "execute_tool_calls",
    "simplify_inference_tool_schema",
    "simplify_messages_input_schema",
    "ToolCall",
    "GatewayToolError",
    "GatewayProtocolError",
    "ToolErrorClass",
    "ToolResultStatus",
    "RecoveryHint",
    "META_SEARCH",
    "META_INVOKE",
    "META_CODE",
    "META_TOOL_NAMES",
    "DEFAULT_GATEWAY_BASE_URL",
    "resolve_gateway_base_url",
]
