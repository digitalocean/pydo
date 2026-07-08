# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Action Gateway wire layer.

The public SDK surface (``ToolsOperations`` / ``CodeOperations``) only talks
to the small :class:`GatewayTransport` interface. Today the gateway is
consumed over its MCP JSON-RPC endpoints (``/mcp`` and ``/mcp/meta``); when
the REST compatibility endpoints ship, a ``RESTTransport`` implementing the
same two methods can be dropped in without changing any user-facing method
or return shape.

The gateway's MCP handler runs stateless with JSON responses, so
:class:`MCPTransport` is a plain JSON-RPC 2.0 POST per request — no
``initialize`` handshake, no session ids, no SSE parsing.
"""

from __future__ import annotations

import itertools
import json as _json
from typing import Any, Dict, List, Optional

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
    ResourceNotModifiedError,
    map_error,
)
from azure.core.rest import HttpRequest

from pydo.custom_extensions import _wrap

from .custom_models import GatewayProtocolError, GatewayToolError

_ERROR_MAP = {
    401: ClientAuthenticationError,
    404: ResourceNotFoundError,
    409: ResourceExistsError,
    304: ResourceNotModifiedError,
}

MCP_PROTOCOL_VERSION = "2025-06-18"

_MCP_PATH = "/mcp"
_MCP_META_PATH = "/mcp/meta"

_MCP_HEADERS = {
    "Content-Type": "application/json",
    "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
    "Accept": "application/json, text/event-stream",
}


def _response_body_text(response: Any) -> str:
    try:
        if hasattr(response, "read"):
            try:
                response.read()
            except Exception:  # noqa: BLE001
                pass
        body = response.text() if hasattr(response, "text") else response.body()
        if isinstance(body, bytes):
            body = body.decode("utf-8", errors="replace")
        return body or ""
    except Exception:  # noqa: BLE001 — best-effort error detail for callers
        return ""


def _raise_gateway_http_error(response: Any) -> None:
    body = _response_body_text(response)
    map_error(
        status_code=response.status_code,
        response=response,
        error_map=_ERROR_MAP,
    )
    message = body.strip() or getattr(response, "reason", None) or "request failed"
    if response.status_code == 412:
        message = (
            "team is not enabled for the Action Infra release "
            f"(412 Precondition Failed): {message}"
        )
    raise HttpResponseError(message=message, response=response)


def _content_text(content: Optional[List[Dict[str, Any]]]) -> str:
    parts = []
    for block in content or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text") or "")
    return "\n".join(p for p in parts if p)


def _unwrap_call_result(result: Dict[str, Any]) -> Any:
    """Normalize an MCP ``tools/call`` result to its useful payload.

    Prefers ``structuredContent`` (typed payload); falls back to the joined
    ``content`` text blocks (parsed as JSON when possible). Raises
    :class:`GatewayToolError` when the tool reported ``isError``.
    """
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


def _parse_jsonrpc(body: Any) -> Dict[str, Any]:
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    try:
        envelope = _json.loads(body)
    except (TypeError, ValueError) as exc:
        raise GatewayProtocolError(
            f"gateway returned a non-JSON response: {body!r}"
        ) from exc
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


class GatewayTransport:
    """Swappable wire layer; MCP semantics are the lowest common denominator."""

    def list_tools(self, *, meta: bool) -> List[Any]:
        raise NotImplementedError

    def call_tool(self, name: str, arguments: Dict[str, Any], *, meta: bool) -> Any:
        raise NotImplementedError


class MCPTransport(GatewayTransport):
    """JSON-RPC 2.0 over plain HTTP POST to ``/mcp`` and ``/mcp/meta``."""

    def __init__(self, base_url_proxy: Any):
        self._client = base_url_proxy
        self._ids = itertools.count(1)

    # -- wire plumbing ----------------------------------------------------

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = HttpRequest(
            "POST",
            path,
            headers=dict(_MCP_HEADERS),
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

    # -- GatewayTransport -------------------------------------------------

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
    "MCPTransport",
    "MCP_PROTOCOL_VERSION",
]
