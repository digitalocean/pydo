# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async Action Gateway operations (mirror of :mod:`pydo.gateway`)."""

from __future__ import annotations

import itertools
from typing import Any, Dict, List, Optional, Sequence, Union

from azure.core.rest import HttpRequest

from pydo.custom_extensions import _wrap
from pydo.gateway.custom_models import (
    META_CODE,
    META_INVOKE,
    META_SEARCH,
    META_TOOL_NAMES,
    GatewayToolError,
)
from pydo.gateway.custom_operations import (
    QueryInput,
    ToolSpecInput,
    _normalize_invoke_entry,
    _normalize_queries,
    _normalize_tool_specs,
    _result_output_or_raise,
    _flatten_search_results,
    _tool_name,
    normalize_invoke_arguments,
)
from pydo.gateway.providers import _error_payload, _get
from pydo.gateway.transport import (
    _MCP_HEADERS,
    _MCP_META_PATH,
    _MCP_PATH,
    _parse_jsonrpc,
    _raise_gateway_http_error,
    _unwrap_call_result,
)


class AsyncGatewayTransport:
    """Async counterpart of :class:`pydo.gateway.transport.GatewayTransport`."""

    async def list_tools(self, *, meta: bool) -> List[Any]:
        raise NotImplementedError

    async def call_tool(
        self, name: str, arguments: Dict[str, Any], *, meta: bool
    ) -> Any:
        raise NotImplementedError


class AsyncMCPTransport(AsyncGatewayTransport):
    """Async JSON-RPC 2.0 over plain HTTP POST to ``/mcp`` and ``/mcp/meta``."""

    def __init__(self, base_url_proxy: Any):
        self._client = base_url_proxy
        self._ids = itertools.count(1)

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = HttpRequest(
            "POST",
            path,
            headers=dict(_MCP_HEADERS),
            json=payload,
        )
        request.url = self._client.format_url(request.url)
        pipeline_response = await self._client._pipeline.run(request)
        response = pipeline_response.http_response
        if response.status_code != 200:
            try:
                await response.read()
            except Exception:  # noqa: BLE001
                pass
            _raise_gateway_http_error(response)
        body = await response.read()
        return _parse_jsonrpc(body)

    async def _rpc(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        meta: bool,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": next(self._ids),
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        return await self._post(_MCP_META_PATH if meta else _MCP_PATH, payload)

    async def list_tools(self, *, meta: bool) -> List[Any]:
        result = await self._rpc("tools/list", meta=meta)
        return _wrap(result.get("tools") or [])

    async def call_tool(
        self, name: str, arguments: Dict[str, Any], *, meta: bool
    ) -> Any:
        result = await self._rpc(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
            meta=meta,
        )
        return _unwrap_call_result(result)


class AsyncToolsOperations:
    """Async Action Gateway tool discovery and invocation."""

    def __init__(self, transport: AsyncGatewayTransport, provider: Any = None):
        self._transport = transport
        self._provider = provider

    async def list(self, *, include_all: bool = False) -> Any:
        return await self._transport.list_tools(meta=not include_all)

    async def search(
        self,
        queries: Union[QueryInput, Sequence[QueryInput]],
        *,
        providers: Optional[Sequence[str]] = None,
        tags: Optional[Sequence[str]] = None,
        limit: Optional[int] = None,
    ) -> Any:
        arguments: Dict[str, Any] = {"queries": _normalize_queries(queries)}
        if providers:
            arguments["providers"] = list(providers)
        if tags:
            arguments["tags"] = list(tags)
        if limit is not None:
            arguments["limit"] = limit
        return await self._transport.call_tool(META_SEARCH, arguments, meta=True)

    async def invoke(
        self,
        tools: Sequence[ToolSpecInput],
        *,
        rationale: Optional[str] = None,
    ) -> Any:
        arguments: Dict[str, Any] = {"tools": _normalize_tool_specs(tools)}
        if rationale:
            arguments["rationale"] = rationale
        return await self._transport.call_tool(META_INVOKE, arguments, meta=True)

    async def invoke_one(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        *,
        rationale: Optional[str] = None,
    ) -> Any:
        envelope = await self.invoke(
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

    async def call(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        return await self._transport.call_tool(name, arguments or {}, meta=False)

    async def __call__(
        self,
        *,
        include_all: bool = False,
        names: Optional[Sequence[str]] = None,
        search: Optional[Union[QueryInput, Sequence[QueryInput]]] = None,
        providers: Optional[Sequence[str]] = None,
        tags: Optional[Sequence[str]] = None,
        limit: Optional[int] = None,
    ) -> List[Any]:
        if self._provider is None:
            raise RuntimeError(
                "no gateway provider configured; pass gateway_provider= to "
                "Client() or use tools.list()/tools.invoke() directly"
            )
        if search is not None:
            payload = await self.search(
                search, providers=providers, tags=tags, limit=limit
            )
            catalog: List[Any] = _flatten_search_results(payload)
        else:
            wants_concrete = include_all or bool(names)
            tools = await self.list(include_all=wants_concrete)
            if names:
                wanted = set(names)
                tools = [t for t in tools if _tool_name(t) in wanted]
                missing = wanted - {_tool_name(t) for t in tools}
                if missing:
                    raise LookupError(f"tools not found in catalog: {sorted(missing)}")
            catalog = list(tools)
        return self._provider.wrap_tools(catalog)


class AsyncCodeOperations:
    """Async ephemeral Python sandbox execution (``action.code``)."""

    def __init__(self, transport: AsyncGatewayTransport):
        self._transport = transport

    async def execute(self, code: str, *, thought: Optional[str] = None) -> Any:
        if not code or not code.strip():
            raise ValueError("code is empty")
        arguments: Dict[str, Any] = {"code": code}
        if thought:
            arguments["thought"] = thought
        return await self._transport.call_tool(META_CODE, arguments, meta=True)


async def async_execute_tool_calls(
    calls: Sequence[Any],
    tools_operations: AsyncToolsOperations,
    *,
    rationale: Optional[str] = None,
) -> List[Any]:
    """Async twin of :func:`pydo.gateway.providers.execute_tool_calls`."""
    results: List[Any] = [None] * len(calls)
    concrete: List[int] = []

    for index, call in enumerate(calls):
        if call.name in META_TOOL_NAMES:
            try:
                arguments = call.arguments
                if call.name == META_INVOKE:
                    arguments = normalize_invoke_arguments(arguments)
                results[index] = await tools_operations._transport.call_tool(
                    call.name, arguments, meta=True
                )
            except (GatewayToolError, TypeError, ValueError) as exc:
                results[index] = _error_payload(exc)
        else:
            concrete.append(index)

    if concrete:
        try:
            batch = [
                _normalize_invoke_entry(
                    {"tool": calls[i].name, "arguments": calls[i].arguments}
                )
                for i in concrete
            ]
        except (TypeError, ValueError) as exc:
            error = _error_payload(exc)
            for index in concrete:
                results[index] = error
            return results
        envelope = await tools_operations.invoke(batch, rationale=rationale)
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


__all__ = [
    "AsyncGatewayTransport",
    "AsyncMCPTransport",
    "AsyncToolsOperations",
    "AsyncCodeOperations",
    "async_execute_tool_calls",
]
