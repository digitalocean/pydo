# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Action Gateway wire layer.

The public SDK surface (``ToolsOperations`` / ``CodeOperations``) only talks
to the small :class:`GatewayTransport` interface. The default transport is
REST (``/tools/search``, ``/tools/invoke``, ``/code/execute``) and requires
a session id via ``X-Session-Id``. An :class:`MCPTransport` remains available
for callers that need JSON-RPC over ``/mcp`` / ``/mcp/meta``.
"""

from __future__ import annotations

import itertools
import json as _json
import os
from typing import Any, Dict, List, Optional

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
    ResourceNotModifiedError,
)
from azure.core.rest import HttpRequest

from pydo.custom_extensions import _wrap

from .custom_models import (
    META_CODE,
    META_INVOKE,
    META_SEARCH,
    GatewayProtocolError,
    GatewayToolError,
    ToolResultStatus,
)

DEFAULT_GATEWAY_BASE_URL = "https://actions.do-ai.run"
_ENV_VAR = "PYDO_GATEWAY_ENDPOINT"


def resolve_gateway_base_url(explicit: Optional[str] = None) -> str:
    url = explicit or os.environ.get(_ENV_VAR) or DEFAULT_GATEWAY_BASE_URL
    url = url.rstrip("/")
    if "://" not in url:
        url = f"https://{url}"
    return url


_ERROR_MAP = {
    401: ClientAuthenticationError,
    404: ResourceNotFoundError,
    409: ResourceExistsError,
    304: ResourceNotModifiedError,
}

MCP_PROTOCOL_VERSION = "2025-06-18"
SESSION_ID_HEADER = "X-Session-Id"

_MCP_PATH = "/mcp"
_MCP_META_PATH = "/mcp/meta"
_REST_TOOLS_PATH = "/tools"
_REST_SEARCH_PATH = "/tools/search"
_REST_INVOKE_PATH = "/tools/invoke"
_REST_CODE_PATH = "/code/execute"

_MCP_HEADERS = {
    "Content-Type": "application/json",
    "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
    "Accept": "application/json, text/event-stream",
}

_REST_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Static meta-tool catalog for REST list(meta=True). Mirrors /mcp/meta.
_META_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": META_SEARCH,
        "title": "Action Search",
        "description": (
            "Discover the catalog tools needed to satisfy one or more user "
            "use cases. Call this before action_invoke whenever you need a "
            "catalog tool you do not already have."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "properties": {
                            "use_case": {"type": "string"},
                            "known_fields": {"type": "string"},
                        },
                        "required": ["use_case"],
                    },
                },
                "providers": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
            },
            "required": ["queries"],
        },
    },
    {
        "name": META_INVOKE,
        "title": "Action Invoke",
        "description": "Invoke 1–10 catalog tools in parallel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tools": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 10,
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {"type": "string"},
                            "tool_slug": {"type": "string"},
                            "arguments": {"type": "object"},
                        },
                        "anyOf": [
                            {"required": ["tool"]},
                            {"required": ["tool_slug"]},
                        ],
                    },
                },
                "rationale": {"type": "string", "maxLength": 512},
            },
            "required": ["tools"],
        },
    },
    {
        "name": META_CODE,
        "title": "Action Code",
        "description": (
            "Run Python in an ephemeral sandbox. Use for computation, "
            "parsing, or data processing — no prior action_search needed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "code_to_execute": {"type": "string"},
                "thought": {"type": "string"},
            },
            "anyOf": [
                {"required": ["code"]},
                {"required": ["code_to_execute"]},
            ],
        },
    },
]


def _response_body_text(response: Any) -> str:
    try:
        body = response.text() if hasattr(response, "text") else response.body()
        if isinstance(body, bytes):
            body = body.decode("utf-8", errors="replace")
        return body or ""
    except Exception:  # noqa: BLE001 — best-effort error detail for callers
        return ""


def _raise_gateway_http_error(response: Any) -> None:
    body = _response_body_text(response)
    message = body.strip() or getattr(response, "reason", None) or "request failed"
    if response.status_code == 412:
        message = (
            "team is not enabled for the Action Infra release "
            f"(412 Precondition Failed): {message}"
        )
    if response.status_code == 404 and "/v2/action-gateway/sessions" in (
        getattr(getattr(response, "request", None), "url", "") or ""
    ):
        message = (
            "session create returned 404 — is POST /v2/action-gateway/sessions "
            f"available on this API endpoint? {message}"
        )
    error_type = _ERROR_MAP.get(response.status_code)
    if error_type:
        raise error_type(
            message=message,
            response=response,
            error_format=lambda _body: None,
        )
    raise HttpResponseError(message=message, response=response)


def _content_text(content: Optional[List[Dict[str, Any]]]) -> str:
    parts = []
    for block in content or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text") or "")
    return "\n".join(p for p in parts if p)


def _unwrap_call_result(result: Dict[str, Any]) -> Any:
    """Normalize an MCP ``tools/call`` result to its useful payload."""
    if result.get("isError"):
        structured = result.get("structuredContent")
        error = None
        if isinstance(structured, dict):
            error = structured.get("error") or (
                structured if "message" in structured else None
            )
        if error:
            raise GatewayToolError.from_error_payload(
                error,
                invocation_id=(
                    structured.get("invocation_id")
                    if isinstance(structured, dict)
                    else None
                ),
            )
        raise GatewayToolError(
            _content_text(result.get("content")) or "tool call failed"
        )

    structured = result.get("structuredContent")
    if structured is not None:
        return _wrap(structured)

    text = _content_text(result.get("content"))
    try:
        return _wrap(_json.loads(text))
    except (TypeError, ValueError):
        return text


def _parse_json_body(body: Any) -> Any:
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    if isinstance(body, (dict, list)):
        return body
    try:
        return _json.loads(body)
    except (TypeError, ValueError) as exc:
        raise GatewayProtocolError(
            f"gateway returned a non-JSON response: {body!r}"
        ) from exc


def _parse_jsonrpc(body: Any) -> Dict[str, Any]:
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    if isinstance(body, str) and any(
        line.startswith("data:") for line in body.splitlines()
    ):
        events = []
        data_lines = []
        for line in body.splitlines():
            if not line:
                if data_lines:
                    events.append("\n".join(data_lines))
                    data_lines = []
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if data_lines:
            events.append("\n".join(data_lines))
        for event in events:
            try:
                candidate = _parse_json_body(event)
            except GatewayProtocolError:
                continue
            if isinstance(candidate, dict) and (
                "result" in candidate or "error" in candidate
            ):
                body = candidate
                break
    envelope = _parse_json_body(body)
    if not isinstance(envelope, dict):
        raise GatewayProtocolError(
            f"gateway returned an unexpected JSON-RPC envelope: {envelope!r}"
        )
    error = envelope.get("error")
    if error:
        raise GatewayProtocolError(
            error.get("message") or "JSON-RPC error",
            code=error.get("code"),
            data=error.get("data"),
        )
    result = envelope.get("result")
    if not isinstance(result, dict):
        raise GatewayProtocolError(
            f"gateway JSON-RPC response is missing a result: {envelope!r}"
        )
    return result


def _decode_output(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        try:
            return _json.loads(value)
        except (TypeError, ValueError):
            return value
    return value


def _unwrap_tool_result(payload: Any) -> Any:
    """Unwrap a REST ``ToolResult`` envelope; raise on failure."""
    if not isinstance(payload, dict):
        return _wrap(payload)
    status = payload.get("status")
    if status and status != ToolResultStatus.SUCCEEDED:
        error = payload.get("error") or {}
        raise GatewayToolError.from_error_payload(
            dict(error) if isinstance(error, dict) else {"message": str(error)},
            invocation_id=payload.get("invocation_id") or payload.get("call_id"),
        )
    if "output" in payload:
        return _wrap(_decode_output(payload.get("output")))
    return _wrap(payload)


def session_mcp_url(gateway_base_url: str, session_urn: str) -> str:
    """Build the session-pinned MCP URL for external MCP clients."""
    base = gateway_base_url.rstrip("/")
    session_id = session_urn.rsplit(":", 1)[-1]
    return f"{base}/mcp/session/{session_id}"


class GatewayTransport:
    """Swappable wire layer; MCP semantics are the lowest common denominator."""

    def list_tools(self, *, meta: bool) -> List[Any]:
        raise NotImplementedError

    def call_tool(self, name: str, arguments: Dict[str, Any], *, meta: bool) -> Any:
        raise NotImplementedError


class RESTTransport(GatewayTransport):
    """REST over ``/tools``, ``/tools/search``, ``/tools/invoke``, ``/code/execute``.

    Requires ``session_id`` (session URN) on every request via ``X-Session-Id``.
    """

    def __init__(self, base_url_proxy: Any, *, session_id: str):
        if not session_id:
            raise ValueError("session_id is required for RESTTransport")
        self._client = base_url_proxy
        self.session_id = session_id

    def _headers(self) -> Dict[str, str]:
        headers = dict(_REST_HEADERS)
        headers[SESSION_ID_HEADER] = self.session_id
        return headers

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Any:
        kwargs: Dict[str, Any] = {"headers": self._headers()}
        if payload is not None:
            kwargs["json"] = payload
        request = HttpRequest(method, path, **kwargs)
        request.url = self._client.format_url(request.url)
        pipeline_response = self._client._pipeline.run(request)
        response = pipeline_response.http_response
        if response.status_code != 200:
            _raise_gateway_http_error(response)
        body = response.text() if hasattr(response, "text") else response.body()
        return _parse_json_body(body)

    def list_tools(self, *, meta: bool) -> List[Any]:
        if meta:
            return _wrap([dict(tool) for tool in _META_TOOL_DEFINITIONS])
        catalog = self._request("GET", _REST_TOOLS_PATH)
        if isinstance(catalog, dict):
            return _wrap(catalog.get("tools") or [])
        return _wrap(catalog or [])

    def call_tool(self, name: str, arguments: Dict[str, Any], *, meta: bool) -> Any:
        arguments = arguments or {}
        if name == META_SEARCH or (meta and name == META_SEARCH):
            return _unwrap_tool_result(
                self._request("POST", _REST_SEARCH_PATH, arguments)
            )
        if name == META_INVOKE or (meta and name == META_INVOKE):
            # Invoke returns the batch envelope directly (not ToolResult).
            return _wrap(self._request("POST", _REST_INVOKE_PATH, arguments))
        if name == META_CODE or (meta and name == META_CODE):
            return _unwrap_tool_result(
                self._request("POST", _REST_CODE_PATH, arguments)
            )
        # Concrete catalog tool → single-item invoke.
        envelope = self._request(
            "POST",
            _REST_INVOKE_PATH,
            {"tools": [{"tool": name, "arguments": arguments}]},
        )
        results = (envelope or {}).get("results") or []
        if not results:
            raise GatewayToolError(f"invoke of {name!r} returned no results")
        item = results[0]
        item_result = item.get("result") if isinstance(item, dict) else item
        return _unwrap_tool_result(item_result)


class MCPTransport(GatewayTransport):
    """JSON-RPC 2.0 over plain HTTP POST to ``/mcp`` and ``/mcp/meta``."""

    def __init__(self, base_url_proxy: Any, *, session_id: Optional[str] = None):
        self._client = base_url_proxy
        self._ids = itertools.count(1)
        self.session_id = session_id

    def _headers(self) -> Dict[str, str]:
        headers = dict(_MCP_HEADERS)
        if self.session_id:
            headers[SESSION_ID_HEADER] = self.session_id
        return headers

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = HttpRequest(
            "POST",
            path,
            headers=self._headers(),
            json=payload,
        )
        request.url = self._client.format_url(request.url)
        pipeline_response = self._client._pipeline.run(request)
        response = pipeline_response.http_response
        if response.status_code != 200:
            _raise_gateway_http_error(response)
        body = response.text() if hasattr(response, "text") else response.body()
        return _parse_jsonrpc(body)

    def _rpc(
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
        return self._post(_MCP_META_PATH if meta else _MCP_PATH, payload)

    def list_tools(self, *, meta: bool) -> List[Any]:
        result = self._rpc("tools/list", meta=meta)
        return _wrap(result.get("tools") or [])

    def call_tool(self, name: str, arguments: Dict[str, Any], *, meta: bool) -> Any:
        result = self._rpc(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
            meta=meta,
        )
        return _unwrap_call_result(result)


__all__ = [
    "GatewayTransport",
    "RESTTransport",
    "MCPTransport",
    "MCP_PROTOCOL_VERSION",
    "SESSION_ID_HEADER",
    "session_mcp_url",
    "DEFAULT_GATEWAY_BASE_URL",
    "resolve_gateway_base_url",
]
