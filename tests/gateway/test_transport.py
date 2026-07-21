# pylint: disable=missing-function-docstring,protected-access,duplicate-code
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :mod:`pydo.gateway.transport` (REST + MCP wire layers)."""

from __future__ import annotations

import pytest
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)

from pydo.custom_extensions import _BaseURLProxy
from pydo.gateway import (
    GatewayProtocolError,
    GatewayResources,
    GatewayToolError,
    MCPTransport,
    SESSION_ID_HEADER,
)
from pydo.gateway.transport import session_mcp_url

from .conftest import (
    TEST_GATEWAY_URL,
    TEST_SESSION_URN,
    FakeResponse,
    call_result,
    invoke_envelope,
    jsonrpc_error,
    jsonrpc_result,
    make_gateway,
    make_parent,
    sent_payload,
    sent_request,
    tool_result,
)


def test_list_meta_tools_is_local_no_network():
    gateway = make_gateway([])
    tools = gateway.tools.list()
    assert [t.name for t in tools] == [
        "action_search",
        "action_invoke",
        "action_code",
    ]
    assert pipeline_calls(gateway) == 0


def pipeline_calls(gateway) -> int:
    return len(gateway._transport._client._original._pipeline.calls)


def test_list_tools_include_all_hits_rest_catalog():
    gateway = make_gateway([FakeResponse(200, {"tools": [{"name": "web_search"}]})])
    tools = gateway.tools.list(include_all=True)
    request = sent_request(gateway)
    assert request.method == "GET"
    assert request.url.endswith("/tools")
    assert request.headers[SESSION_ID_HEADER] == TEST_SESSION_URN
    assert tools[0].name == "web_search"


def test_search_posts_rest_and_unwraps_tool_result():
    gateway = make_gateway(
        [
            FakeResponse(
                200,
                tool_result({"results": [{"use_case": "x", "results": []}]}),
            )
        ]
    )
    result = gateway.tools.search("search the web")
    request = sent_request(gateway)
    assert request.method == "POST"
    assert request.url.endswith("/tools/search")
    assert request.headers[SESSION_ID_HEADER] == TEST_SESSION_URN
    payload = sent_payload(gateway)
    assert payload["queries"] == [{"use_case": "search the web"}]
    assert result.results[0].use_case == "x"


def test_invoke_posts_rest_envelope():
    gateway = make_gateway([FakeResponse(200, invoke_envelope(output={"ok": True}))])
    result = gateway.tools.invoke(
        [{"tool": "web_search", "arguments": {"query": "do"}}]
    )
    assert sent_request(gateway).url.endswith("/tools/invoke")
    assert result.success_count == 1


def test_code_execute_posts_rest():
    gateway = make_gateway(
        [FakeResponse(200, tool_result({"stdout": "hi", "exit_code": 0}))]
    )
    result = gateway.code.execute("print('hi')")
    assert sent_request(gateway).url.endswith("/code/execute")
    assert result.stdout == "hi"
    assert result.exit_code == 0


def test_concrete_call_routes_through_invoke():
    gateway = make_gateway([FakeResponse(200, invoke_envelope(output={"answer": 42}))])
    result = gateway.tools.call("web_search", {"query": "x"})
    assert sent_request(gateway).url.endswith("/tools/invoke")
    assert result.answer == 42


def test_failed_tool_result_raises():
    gateway = make_gateway(
        [
            FakeResponse(
                200,
                tool_result(
                    error={
                        "class": "rate_limited",
                        "message": "slow down",
                        "retriable": True,
                        "recovery_hint": "backoff",
                    }
                ),
            )
        ]
    )
    with pytest.raises(GatewayToolError) as excinfo:
        gateway.code.execute("1")
    err = excinfo.value
    assert err.error_class == "rate_limited"
    assert err.retriable is True
    assert err.recovery_hint == "backoff"


def test_non_json_body_raises_protocol_error():
    gateway = make_gateway([FakeResponse(200, "<html>nope</html>")])
    with pytest.raises(GatewayProtocolError, match="non-JSON"):
        gateway.tools.list(include_all=True)


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
        gateway.tools.list(include_all=True)


def test_412_message_mentions_release_gate():
    gateway = make_gateway([FakeResponse(412, "nope")])
    with pytest.raises(HttpResponseError, match="Action Infra release"):
        gateway.tools.list(include_all=True)


def test_session_mcp_url_uses_uuid_from_urn():
    session_uuid = "3a12f86f-ef5c-41e3-a951-2b7a933e151d"
    url = session_mcp_url(
        TEST_GATEWAY_URL,
        f"do:managed_agents_session:{session_uuid}",
    )
    assert url == f"https://actions.do-ai-test.run/mcp/session/{session_uuid}"


def test_mcp_transport_still_works_with_session_header():
    parent = make_parent(
        [FakeResponse(200, jsonrpc_result({"tools": [{"name": "action_search"}]}))]
    )
    proxy = _BaseURLProxy(parent._client, TEST_GATEWAY_URL)
    transport = MCPTransport(proxy, session_id=TEST_SESSION_URN)
    gateway = GatewayResources(
        parent,
        gateway_endpoint=TEST_GATEWAY_URL,
        transport=transport,
    )
    tools = gateway.tools.list()
    request = sent_request(gateway)
    assert request.url.endswith("/mcp/meta")
    assert request.headers[SESSION_ID_HEADER] == TEST_SESSION_URN
    assert tools[0].name == "action_search"


def test_mcp_jsonrpc_error_raises_protocol_error():
    parent = make_parent([FakeResponse(200, jsonrpc_error(-32601, "method not found"))])
    proxy = _BaseURLProxy(parent._client, TEST_GATEWAY_URL)
    transport = MCPTransport(proxy, session_id=TEST_SESSION_URN)
    gateway = GatewayResources(
        parent, gateway_endpoint=TEST_GATEWAY_URL, transport=transport
    )
    with pytest.raises(GatewayProtocolError) as excinfo:
        gateway.tools.list()
    assert excinfo.value.code == -32601


def test_mcp_is_error_raises_gateway_tool_error():
    structured = {
        "invocation_id": "inv_1",
        "error": {
            "class": "rate_limited",
            "message": "slow down",
            "retriable": True,
            "recovery_hint": "backoff",
        },
    }
    parent = make_parent(
        [FakeResponse(200, jsonrpc_result(call_result(structured, is_error=True)))]
    )
    proxy = _BaseURLProxy(parent._client, TEST_GATEWAY_URL)
    transport = MCPTransport(proxy, session_id=TEST_SESSION_URN)
    gateway = GatewayResources(
        parent, gateway_endpoint=TEST_GATEWAY_URL, transport=transport
    )
    with pytest.raises(GatewayToolError) as excinfo:
        gateway.tools.call("web_search", {"query": "x"})
    assert excinfo.value.invocation_id == "inv_1"
