# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Action Gateway API — hand-written; preserved across ``make generate``.

Exposes tool discovery/invocation and sandboxed code execution over the
gateway's MCP endpoints, plus Composio-style providers that make gateway
tools plug directly into pydo's inference surfaces (chat completions,
messages, responses).
"""

from __future__ import annotations

import os
from typing import Any, List, Optional, Sequence

from pydo.custom_extensions import _BaseURLProxy

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
from .transport import MCP_PROTOCOL_VERSION, GatewayTransport, MCPTransport

DEFAULT_GATEWAY_BASE_URL = "https://actions.do-ai.run"
_ENV_VAR = "PYDO_GATEWAY_ENDPOINT"


def resolve_gateway_base_url(explicit: Optional[str] = None) -> str:
    url = explicit or os.environ.get(_ENV_VAR) or DEFAULT_GATEWAY_BASE_URL
    url = url.rstrip("/")
    if "://" not in url:
        url = f"https://{url}"
    return url


class GatewayResources:
    """Action Gateway surface attached at ``client.gateway``."""

    def __init__(
        self,
        parent_client: Any,
        *,
        gateway_endpoint: Optional[str] = None,
        provider: Optional[BaseProvider] = None,
        transport: Optional[GatewayTransport] = None,
    ):
        if transport is None:
            proxy = _BaseURLProxy(
                parent_client._client,
                resolve_gateway_base_url(gateway_endpoint),
            )
            transport = MCPTransport(proxy)
        self._transport = transport
        self.provider = provider or default_provider()
        self.tools = ToolsOperations(transport, self.provider)
        self.code = CodeOperations(transport)

    @property
    def base_url(self) -> Optional[str]:
        proxy = getattr(self._transport, "_client", None)
        return getattr(proxy, "_base_url", None)

    def handle_tool_calls(
        self,
        response: Any,
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        """Execute the tool calls in an inference response.

        Extracts tool calls using the configured provider, executes them
        against the gateway (meta-tools directly; concrete tools batched
        through one ``action.invoke``), and returns vendor-formatted
        messages/items ready to append to the conversation. Returns an
        empty list when the response contains no tool calls.
        """
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
        """Execute pre-extracted :class:`ToolCall` objects; return raw outputs."""
        return execute_tool_calls(calls, self.tools, rationale=rationale)


__all__ = [
    "GatewayResources",
    "ToolsOperations",
    "CodeOperations",
    "normalize_invoke_arguments",
    "GatewayTransport",
    "MCPTransport",
    "MCP_PROTOCOL_VERSION",
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
