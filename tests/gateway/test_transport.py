# pylint: disable=missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :mod:`pydo.gateway.transport` (MCP JSON-RPC wire layer)."""

from __future__ import annotations

import pytest
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)

from pydo.gateway import (
    MCP_PROTOCOL_VERSION,
    GatewayProtocolError,
    GatewayToolError,
)

from .conftest import (
    FakeResponse,
    call_result,
    jsonrpc_error,
    jsonrpc_result,
    make_gateway,
    sent_payload,
    sent_request,
)


def test_list_tools_posts_jsonrpc_to_meta_endpoint():
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result({"tools": [{"name": "action.search"}]}))]
    )
    tools = gateway.tools.list()

    request = sent_request(gateway)
    assert request.method == "POST"
    assert request.url.endswith("/mcp/meta")
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["MCP-Protocol-Version"] == MCP_PROTOCOL_VERSION
    assert request.headers["Accept"] == "application/json, text/event-stream"

    payload = sent_payload(gateway)
    assert payload["jsonrpc"] == "2.0"
    assert payload["method"] == "tools/list"
    assert isinstance(payload["id"], int)

    assert tools[0].name == "action.search"


def test_list_tools_include_all_hits_concrete_endpoint():
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result({"tools": [{"name": "web_search"}]}))]
    )
    gateway.tools.list(include_all=True)
    assert sent_request(gateway).url.endswith("/mcp")


def test_call_tool_prefers_structured_content():
    structured = {"stdout": "hi", "exit_code": 0}
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result(call_result(structured, text="hi")))]
    )
    result = gateway.code.execute("print('hi')")
    assert result.stdout == "hi"
    assert result.exit_code == 0


def test_call_tool_falls_back_to_content_text():
    gateway = make_gateway(
        [
            FakeResponse(
                200,
                jsonrpc_result(
                    {"isError": False, "content": [{"type": "text", "text": "plain"}]}
                ),
            )
        ]
    )
    result = gateway.tools.call("web_fetch", {"url": "https://example.com"})
    assert result == "plain"


def test_call_tool_content_text_parsed_as_json_when_possible():
    gateway = make_gateway(
        [
            FakeResponse(
                200,
                jsonrpc_result(
                    {
                        "isError": False,
                        "content": [{"type": "text", "text": '{"answer": 42}'}],
                    }
                ),
            )
        ]
    )
    result = gateway.tools.call("web_fetch", {"url": "https://example.com"})
    assert result.answer == 42


def test_is_error_raises_gateway_tool_error_with_taxonomy():
    structured = {
        "invocation_id": "inv_1",
        "error": {
            "class": "rate_limited",
            "message": "slow down",
            "retriable": True,
            "recovery_hint": "backoff",
        },
    }
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result(call_result(structured, is_error=True)))]
    )
    with pytest.raises(GatewayToolError) as excinfo:
        gateway.tools.call("web_search", {"query": "x"})
    err = excinfo.value
    assert err.error_class == "rate_limited"
    assert err.retriable is True
    assert err.recovery_hint == "backoff"
    assert err.invocation_id == "inv_1"


def test_is_error_without_structure_uses_content_text():
    gateway = make_gateway(
        [
            FakeResponse(
                200,
                jsonrpc_result(
                    {"isError": True, "content": [{"type": "text", "text": "boom"}]}
                ),
            )
        ]
    )
    with pytest.raises(GatewayToolError, match="boom"):
        gateway.tools.call("web_search", {"query": "x"})


def test_jsonrpc_error_raises_protocol_error():
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_error(-32601, "method not found"))]
    )
    with pytest.raises(GatewayProtocolError) as excinfo:
        gateway.tools.list()
    assert excinfo.value.code == -32601


def test_non_json_body_raises_protocol_error():
    gateway = make_gateway([FakeResponse(200, "<html>nope</html>")])
    with pytest.raises(GatewayProtocolError, match="non-JSON"):
        gateway.tools.list()


@pytest.mark.parametrize(
    "status,exc",
    [
        (401, ClientAuthenticationError),
        (404, ResourceNotFoundError),
        (400, HttpResponseError),
        (412, HttpResponseError),
    ],
)
def test_http_errors_are_mapped(status, exc):
    gateway = make_gateway([FakeResponse(status, {"type": "invalid_request"})])
    with pytest.raises(exc):
        gateway.tools.list()


def test_412_message_mentions_release_gate():
    gateway = make_gateway([FakeResponse(412, "nope")])
    with pytest.raises(HttpResponseError, match="Action Infra release"):
        gateway.tools.list()


def test_request_ids_increment():
    gateway = make_gateway(
        [
            FakeResponse(200, jsonrpc_result({"tools": []}, rpc_id=1)),
            FakeResponse(200, jsonrpc_result({"tools": []}, rpc_id=2)),
        ]
    )
    gateway.tools.list()
    gateway.tools.list()
    first = sent_payload(gateway, 0)
    second = sent_payload(gateway, 1)
    assert second["id"] == first["id"] + 1
