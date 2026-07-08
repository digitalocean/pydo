# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Action Gateway operations (tools + sandboxed code execution).

Every method delegates to a :class:`~pydo.gateway.transport.GatewayTransport`,
so the public return shapes hold regardless of the underlying wire protocol
(MCP JSON-RPC today, REST later).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from .custom_models import (
    META_CODE,
    META_INVOKE,
    META_SEARCH,
    GatewayToolError,
    ToolResultStatus,
)
from .transport import GatewayTransport

_MAX_SEARCH_QUERIES = 5
_MAX_INVOKE_TOOLS = 10

QueryInput = Union[str, Dict[str, Any]]
ToolSpecInput = Dict[str, Any]


def _normalize_queries(
    queries: Union[QueryInput, Sequence[QueryInput]],
) -> List[Dict[str, Any]]:
    """Accept a single use-case str, a list of strs, or dicts with ``use_case``."""
    if isinstance(queries, (str, dict)):
        queries = [queries]
    normalized: List[Dict[str, Any]] = []
    for query in queries:
        if isinstance(query, str):
            entry: Dict[str, Any] = {"use_case": query}
        elif isinstance(query, dict):
            if not query.get("use_case"):
                raise ValueError("each search query dict requires a 'use_case'")
            entry = {"use_case": query["use_case"]}
            if query.get("known_fields"):
                entry["known_fields"] = query["known_fields"]
        else:
            raise TypeError("queries must be str or dict entries")
        normalized.append(entry)
    if not 1 <= len(normalized) <= _MAX_SEARCH_QUERIES:
        raise ValueError(f"search accepts between 1 and {_MAX_SEARCH_QUERIES} queries")
    return normalized


def _normalize_tool_specs(tools: Sequence[ToolSpecInput]) -> List[Dict[str, Any]]:
    """Normalize invoke entries; ``tool_slug`` is accepted as alias for ``tool``."""
    normalized: List[Dict[str, Any]] = []
    for spec in tools:
        if not isinstance(spec, dict):
            raise TypeError(
                "each invoke entry must be a dict like "
                "{'tool': name, 'arguments': {...}}"
            )
        name = spec.get("tool") or spec.get("tool_slug")
        if not name:
            raise ValueError("each invoke entry requires a 'tool' name")
        normalized.append({"tool": name, "arguments": spec.get("arguments") or {}})
    if not 1 <= len(normalized) <= _MAX_INVOKE_TOOLS:
        raise ValueError(f"invoke accepts between 1 and {_MAX_INVOKE_TOOLS} tools")
    return normalized


def _result_output_or_raise(item_result: Any, tool_name: str) -> Any:
    """Unwrap one invoke ``ToolResult`` envelope; raise on failure."""
    get = getattr(item_result, "get", None)
    if get is None:
        return item_result
    status = get("status")
    if status and status != ToolResultStatus.SUCCEEDED:
        error = get("error") or {}
        raise GatewayToolError.from_error_payload(
            dict(error) if error else {"message": f"tool {tool_name!r} failed"},
            invocation_id=get("invocation_id"),
        )
    return get("output")


class ToolsOperations:
    """Action Gateway tool discovery and invocation.

    Calling the instance itself (``client.gateway.tools()``) returns
    provider-formatted tool definitions ready for an inference ``tools=``
    parameter — see :mod:`pydo.gateway.providers`.
    """

    def __init__(self, transport: GatewayTransport, provider: Any = None):
        self._transport = transport
        self._provider = provider

    # -- discovery ---------------------------------------------------------

    def list(self, *, include_all: bool = False) -> Any:
        """List available tools.

        By default returns the three meta-tools (``action.search``,
        ``action.invoke``, ``action.code``) — the intended agent workflow.
        Pass ``include_all=True`` for the full concrete tool catalog.
        """
        return self._transport.list_tools(meta=not include_all)

    def search(
        self,
        queries: Union[QueryInput, Sequence[QueryInput]],
        *,
        providers: Optional[Sequence[str]] = None,
        tags: Optional[Sequence[str]] = None,
        limit: Optional[int] = None,
    ) -> Any:
        """Search the tool catalog by use case (``action.search``).

        :param queries: A use-case string, a list of strings, or dicts with
            ``use_case`` (and optional ``known_fields``). 1–5 queries.
        :param providers: Optional provider filters (e.g. ``["exa"]``).
        :param tags: Optional tag filters.
        :param limit: Per-query result cap.
        """
        arguments: Dict[str, Any] = {"queries": _normalize_queries(queries)}
        if providers:
            arguments["providers"] = list(providers)
        if tags:
            arguments["tags"] = list(tags)
        if limit is not None:
            arguments["limit"] = limit
        return self._transport.call_tool(META_SEARCH, arguments, meta=True)

    # -- execution ---------------------------------------------------------

    def invoke(
        self,
        tools: Sequence[ToolSpecInput],
        *,
        rationale: Optional[str] = None,
    ) -> Any:
        """Invoke 1–10 tools in parallel (``action.invoke``).

        Returns the full envelope (``total_count`` / ``success_count`` /
        ``error_count`` / ``results[]``). Per-tool failures are reported
        inside the envelope and do NOT raise.
        """
        arguments: Dict[str, Any] = {"tools": _normalize_tool_specs(tools)}
        if rationale:
            arguments["rationale"] = rationale
        return self._transport.call_tool(META_INVOKE, arguments, meta=True)

    def invoke_one(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        *,
        rationale: Optional[str] = None,
    ) -> Any:
        """Invoke a single tool and return its output directly.

        Raises :class:`GatewayToolError` if the tool failed.
        """
        envelope = self.invoke(
            [{"tool": name, "arguments": arguments or {}}],
            rationale=rationale,
        )
        get = getattr(envelope, "get", None)
        results = (get("results") if get else None) or []
        if not results:
            raise GatewayToolError(f"invoke of {name!r} returned no results")
        first = results[0]
        item_result = (getattr(first, "get", lambda *_: first)("result")) or first
        return _result_output_or_raise(item_result, name)

    def call(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call one concrete catalog tool directly (``tools/call`` on ``/mcp``).

        Unlike :meth:`invoke`, the result is the tool's output payload with
        no invoke envelope; failures raise :class:`GatewayToolError`.
        """
        return self._transport.call_tool(name, arguments or {}, meta=False)

    # -- inference integration (Composio-style) -----------------------------

    def __call__(
        self,
        *,
        include_all: bool = False,
        names: Optional[Sequence[str]] = None,
        search: Optional[Union[QueryInput, Sequence[QueryInput]]] = None,
        providers: Optional[Sequence[str]] = None,
        tags: Optional[Sequence[str]] = None,
        limit: Optional[int] = None,
    ) -> List[Any]:
        """Return provider-formatted tool definitions for ``tools=``.

        By default wraps the three meta-tools so the model drives the
        search → invoke → code workflow itself. Pass ``include_all=True``,
        ``names=``, or ``search=`` to wrap concrete catalog tools instead.
        """
        if self._provider is None:
            raise RuntimeError(
                "no gateway provider configured; pass gateway_provider= to "
                "Client() or use tools.list()/tools.invoke() directly"
            )
        catalog = self._fetch_catalog(
            include_all=include_all,
            names=names,
            search=search,
            providers=providers,
            tags=tags,
            limit=limit,
        )
        return self._provider.wrap_tools(catalog)

    def _fetch_catalog(
        self,
        *,
        include_all: bool,
        names: Optional[Sequence[str]],
        search: Optional[Union[QueryInput, Sequence[QueryInput]]],
        providers: Optional[Sequence[str]],
        tags: Optional[Sequence[str]],
        limit: Optional[int],
    ) -> List[Any]:
        if search is not None:
            payload = self.search(search, providers=providers, tags=tags, limit=limit)
            return _flatten_search_results(payload)
        wants_concrete = include_all or bool(names)
        tools = self.list(include_all=wants_concrete)
        if names:
            wanted = set(names)
            tools = [t for t in tools if _tool_name(t) in wanted]
            missing = wanted - {_tool_name(t) for t in tools}
            if missing:
                raise LookupError(f"tools not found in catalog: {sorted(missing)}")
        return list(tools)


def _tool_name(tool: Any) -> Optional[str]:
    get = getattr(tool, "get", None)
    return get("name") if get else getattr(tool, "name", None)


def _flatten_search_results(payload: Any) -> List[Any]:
    """Flatten an ``action.search`` payload into a deduplicated tool list."""
    get = getattr(payload, "get", None)
    groups = (get("results") if get else None) or []
    seen: Dict[str, Any] = {}
    for group in groups:
        group_get = getattr(group, "get", None)
        matches = (group_get("results") if group_get else None) or []
        for match in matches:
            name = _tool_name(match)
            if name and name not in seen:
                seen[name] = match
    return list(seen.values())


class CodeOperations:
    """Ephemeral Python sandbox execution (``action.code``)."""

    def __init__(self, transport: GatewayTransport):
        self._transport = transport

    def execute(self, code: str, *, thought: Optional[str] = None) -> Any:
        """Run Python code in the gateway sandbox.

        Returns the execution output (``stdout`` / ``stderr`` /
        ``exit_code``). Raises :class:`GatewayToolError` on sandbox failure.
        """
        if not code or not code.strip():
            raise ValueError("code is empty")
        arguments: Dict[str, Any] = {"code": code}
        if thought:
            arguments["thought"] = thought
        return self._transport.call_tool(META_CODE, arguments, meta=True)


__all__ = [
    "ToolsOperations",
    "CodeOperations",
]
