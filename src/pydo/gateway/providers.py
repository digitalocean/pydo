# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Inference providers — translate gateway tools to/from vendor formats.

pydo exposes three inference surfaces with three different tool wire
formats. A provider owns both directions of translation for one of them
(the Composio pattern):

* :class:`ChatCompletionsProvider` — ``client.chat.completions.create``
  (OpenAI chat completions format). The default.
* :class:`MessagesProvider` — ``client.messages.create`` (Anthropic
  Messages format).
* :class:`ResponsesProvider` — ``client.responses.create`` (OpenAI
  Responses format).

Usage::

    client = Client(token=..., gateway_provider=MessagesProvider())
    tools = client.gateway.tools()                 # vendor tools= format
    resp = client.messages.create(..., tools=tools, messages=messages)
    messages += client.gateway.handle_tool_calls(resp)
"""

from __future__ import annotations

import json as _json
from typing import Any, Dict, List, Optional, Sequence

from .custom_models import ToolCall


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Uniform field access over dicts/DotDicts and attribute objects."""
    getter = getattr(obj, "get", None)
    if getter is not None:
        return getter(key, default)
    return getattr(obj, key, default)


def _decode_arguments(arguments: Any) -> Dict[str, Any]:
    if isinstance(arguments, str):
        if not arguments.strip():
            return {}
        return _json.loads(arguments)
    if isinstance(arguments, dict):
        return dict(arguments)
    return {}


def _tool_fields(tool: Any) -> Dict[str, Any]:
    """Extract canonical fields from a gateway catalog/meta tool definition."""
    return {
        "name": _get(tool, "name"),
        "description": _get(tool, "description") or _get(tool, "title") or "",
        "parameters": dict(_get(tool, "inputSchema") or {"type": "object"}),
    }


def _result_to_content(result: Any) -> str:
    """Serialize one tool result (output or error payload) for the model."""
    if isinstance(result, str):
        return result
    try:
        return _json.dumps(result, default=str)
    except (TypeError, ValueError):
        return str(result)


class BaseProvider:
    """Translation contract between gateway tools and one inference surface."""

    name = "base"

    def wrap_tools(self, catalog_tools: Sequence[Any]) -> List[Dict[str, Any]]:
        """Convert canonical gateway tool defs to the vendor ``tools=`` format."""
        raise NotImplementedError

    def extract_tool_calls(self, response: Any) -> List[ToolCall]:
        """Extract normalized tool calls from a vendor response object."""
        raise NotImplementedError

    def format_tool_results(
        self,
        calls: Sequence[ToolCall],
        results: Sequence[Any],
    ) -> List[Dict[str, Any]]:
        """Convert invocation outputs into vendor-shaped result messages/items."""
        raise NotImplementedError


class ChatCompletionsProvider(BaseProvider):
    """OpenAI chat-completions format (``client.chat.completions.create``)."""

    name = "chat.completions"

    def wrap_tools(self, catalog_tools: Sequence[Any]) -> List[Dict[str, Any]]:
        return [
            {"type": "function", "function": _tool_fields(tool)}
            for tool in catalog_tools
        ]

    def extract_tool_calls(self, response: Any) -> List[ToolCall]:
        choices = _get(response, "choices") or []
        if not choices:
            return []
        message = _get(choices[0], "message") or {}
        calls = []
        for tool_call in _get(message, "tool_calls") or []:
            function = _get(tool_call, "function") or {}
            calls.append(
                ToolCall(
                    call_id=_get(tool_call, "id") or "",
                    name=_get(function, "name") or "",
                    arguments=_decode_arguments(_get(function, "arguments")),
                )
            )
        return calls

    def format_tool_results(
        self,
        calls: Sequence[ToolCall],
        results: Sequence[Any],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "role": "tool",
                "tool_call_id": call.call_id,
                "content": _result_to_content(result),
            }
            for call, result in zip(calls, results)
        ]


class MessagesProvider(BaseProvider):
    """Anthropic Messages format (``client.messages.create``)."""

    name = "messages"

    def wrap_tools(self, catalog_tools: Sequence[Any]) -> List[Dict[str, Any]]:
        wrapped = []
        for tool in catalog_tools:
            fields = _tool_fields(tool)
            wrapped.append(
                {
                    "name": fields["name"],
                    "description": fields["description"],
                    "input_schema": fields["parameters"],
                }
            )
        return wrapped

    def extract_tool_calls(self, response: Any) -> List[ToolCall]:
        calls = []
        for block in _get(response, "content") or []:
            if _get(block, "type") != "tool_use":
                continue
            calls.append(
                ToolCall(
                    call_id=_get(block, "id") or "",
                    name=_get(block, "name") or "",
                    arguments=_decode_arguments(_get(block, "input")),
                )
            )
        return calls

    def format_tool_results(
        self,
        calls: Sequence[ToolCall],
        results: Sequence[Any],
    ) -> List[Dict[str, Any]]:
        if not calls:
            return []
        content = [
            {
                "type": "tool_result",
                "tool_use_id": call.call_id,
                "content": _result_to_content(result),
            }
            for call, result in zip(calls, results)
        ]
        # Anthropic expects all tool results in a single user turn.
        return [{"role": "user", "content": content}]


class ResponsesProvider(BaseProvider):
    """OpenAI Responses format (``client.responses.create``)."""

    name = "responses"

    def wrap_tools(self, catalog_tools: Sequence[Any]) -> List[Dict[str, Any]]:
        return [{"type": "function", **_tool_fields(tool)} for tool in catalog_tools]

    def extract_tool_calls(self, response: Any) -> List[ToolCall]:
        calls = []
        for item in _get(response, "output") or []:
            if _get(item, "type") != "function_call":
                continue
            calls.append(
                ToolCall(
                    call_id=_get(item, "call_id") or _get(item, "id") or "",
                    name=_get(item, "name") or "",
                    arguments=_decode_arguments(_get(item, "arguments")),
                )
            )
        return calls

    def format_tool_results(
        self,
        calls: Sequence[ToolCall],
        results: Sequence[Any],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": _result_to_content(result),
            }
            for call, result in zip(calls, results)
        ]


def default_provider() -> BaseProvider:
    return ChatCompletionsProvider()


def execute_tool_calls(
    calls: Sequence[ToolCall],
    tools_operations: Any,
    *,
    rationale: Optional[str] = None,
) -> List[Any]:
    """Execute normalized tool calls against the gateway.

    Meta-tool calls (``action.search`` / ``action.invoke`` / ``action.code``)
    go straight through; concrete tool names are batched through one
    ``action.invoke``. Per-tool failures become structured error payloads
    rather than raising, so the model can observe and recover.
    """
    from .custom_models import META_TOOL_NAMES, GatewayToolError

    results: List[Any] = [None] * len(calls)
    concrete: List[int] = []

    for index, call in enumerate(calls):
        if call.name in META_TOOL_NAMES:
            try:
                results[index] = tools_operations._transport.call_tool(
                    call.name, call.arguments, meta=True
                )
            except GatewayToolError as exc:
                results[index] = _error_payload(exc)
        else:
            concrete.append(index)

    if concrete:
        batch = [
            {"tool": calls[i].name, "arguments": calls[i].arguments} for i in concrete
        ]
        envelope = tools_operations.invoke(batch, rationale=rationale)
        items = (_get(envelope, "results") or []) if envelope is not None else []
        for position, index in enumerate(concrete):
            if position < len(items):
                item = items[position]
                item_result = _get(item, "result") or item
                status = _get(item_result, "status")
                if status and status != "succeeded":
                    results[index] = {
                        "error": _get(item_result, "error")
                        or {"message": f"tool {calls[index].name!r} failed"}
                    }
                else:
                    results[index] = _get(item_result, "output")
            else:
                results[index] = {
                    "error": {"message": "no result returned for this tool call"}
                }
    return results


def _error_payload(exc: Any) -> Dict[str, Any]:
    return {
        "error": {
            "message": str(exc),
            "class": getattr(exc, "error_class", None),
            "retriable": getattr(exc, "retriable", None),
            "recovery_hint": getattr(exc, "recovery_hint", None),
        }
    }


__all__ = [
    "BaseProvider",
    "ChatCompletionsProvider",
    "MessagesProvider",
    "ResponsesProvider",
    "default_provider",
    "execute_tool_calls",
]
