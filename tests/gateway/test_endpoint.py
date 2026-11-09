# pylint: disable=missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for Action Gateway endpoints and endpoint versions."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlsplit

import pytest

import pydo.operations
from pydo.action_gateway import ActionGatewayClient
from pydo.gateway import (
    ACTOR_ID_HEADER,
    SESSION_ID_HEADER,
    EndpointMCPTransport,
    EndpointsOperations,
    GatewayProtocolError,
)
from pydo.gateway.transport import _META_TOOL_DEFINITIONS, _endpoint_approval_url

from .conftest import (
    TEST_BACKING_SESSION_ID,
    TEST_ENDPOINT_ID,
    TEST_ENDPOINT_MCP_URL,
    TEST_GATEWAY_URL,
    TEST_VERSION_MCP_URL,
    FakeResponse,
    call_result,
    chat_tool_response,
    endpoint_payload,
    endpoint_publish_response,
    endpoint_version_payload,
    jsonrpc_result,
    make_parent,
)

_VERSION_ID = f"{TEST_ENDPOINT_ID}.v1"

requires_generated = pytest.mark.skipif(
    not hasattr(pydo.operations, "EndpointsOperations"),
    reason="generated endpoint operations arrive with clientgen",
)


def _mock_parent(responses=()):
    parent = make_parent(list(responses))
    parent.endpoints = MagicMock()
    parent.endpoint_versions = MagicMock()
    return parent


def _generated_parent(responses):
    parent = make_parent(responses)
    args = (parent._client, MagicMock(), MagicMock(), MagicMock())
    # Looked up by name so pylint passes before clientgen adds these classes.
    generated = vars(pydo.operations)
    parent.endpoints = generated["EndpointsOperations"](*args)
    parent.endpoint_versions = generated["EndpointVersionsOperations"](*args)
    return parent


def _ops(parent):
    return EndpointsOperations(parent, gateway_endpoint=TEST_GATEWAY_URL)


def _body(request):
    return json.loads(request.content)


def test_create_delegates_to_generated_operation():
    parent = _mock_parent()
    parent.endpoints.create.return_value = endpoint_publish_response()

    endpoint = _ops(parent).create(
        "support-agent",
        actor_id="actor-123",
        tools=["exa_web_search@1"],
        config={"preloadTools": ["exa_web_search@1"]},
        permissions={"default_action": "deny"},
        vpc_uuid="5a4981aa-9653-4bd1-bef5-d6bff52042e4",
        insights={"logs": True},
    )

    assert parent.endpoints.create.call_args.kwargs["body"] == {
        "name": "support-agent",
        "version": {
            "actor_id": "actor-123",
            "policy": {"defaultAction": "deny", "rules": []},
            "tools": ["exa_web_search@1"],
            "config": {"preloadTools": ["exa_web_search@1"]},
            "network": {"vpcUuid": "5a4981aa-9653-4bd1-bef5-d6bff52042e4"},
        },
        "insights": {"logs": True},
    }
    assert endpoint.id == TEST_ENDPOINT_ID
    assert endpoint.name == "support-agent"
    assert endpoint.actor_id == "actor-123"
    assert endpoint.insights == {"logs": True}
    assert endpoint.url == endpoint.mcp_url == TEST_ENDPOINT_MCP_URL
    assert endpoint.head_version.id == _VERSION_ID
    assert endpoint.head_version.version_number == 1
    assert endpoint.head_version.url == TEST_VERSION_MCP_URL
    assert endpoint.version_mcp_url == TEST_VERSION_MCP_URL


def test_create_defaults_policy_and_omits_unset_options():
    parent = _mock_parent()
    parent.endpoints.create.return_value = endpoint_publish_response(actor_id="")

    endpoint = _ops(parent).create("support-agent", actor_id="  ")

    assert parent.endpoints.create.call_args.kwargs["body"] == {
        "name": "support-agent",
        "version": {"policy": {"defaultAction": "ask"}},
    }
    assert endpoint.actor_id is None
    assert endpoint.head_version.actor_id is None


def test_create_validates_arguments():
    ops = _ops(_mock_parent())
    with pytest.raises(ValueError, match="name"):
        ops.create(" ")
    with pytest.raises(TypeError, match="tools"):
        ops.create("a", tools="exa_web_search")
    with pytest.raises(TypeError, match="config"):
        ops.create("a", config=["preloadTools"])
    with pytest.raises(TypeError, match="insights"):
        ops.create("a", insights=True)
    with pytest.raises(ValueError, match="toolbelt permissions"):
        ops.create("a", permissions={"rules": [{"toolbelt": "belt@1"}]})


def test_create_falls_back_to_top_level_mcp_urls():
    payload = endpoint_publish_response()
    del payload["endpoint"]["mcp_url"]
    del payload["version"]["mcp_url"]
    parent = _mock_parent()
    parent.endpoints.create.return_value = payload

    endpoint = _ops(parent).create("support-agent")

    assert endpoint.url == TEST_ENDPOINT_MCP_URL
    assert endpoint.head_version.url == TEST_VERSION_MCP_URL


@pytest.mark.parametrize("missing", ["endpoint", "version"])
def test_create_rejects_incomplete_response(missing):
    payload = endpoint_publish_response()
    del payload[missing]
    parent = _mock_parent()
    parent.endpoints.create.return_value = payload
    with pytest.raises(GatewayProtocolError, match=missing):
        _ops(parent).create("support-agent")


def test_create_rejects_response_without_mcp_url():
    payload = endpoint_publish_response()
    del payload["endpoint"]["mcp_url"]
    del payload["mcp_url"]
    parent = _mock_parent()
    parent.endpoints.create.return_value = payload
    with pytest.raises(GatewayProtocolError, match="mcp_url"):
        _ops(parent).create("support-agent")


def test_get_embeds_head_version():
    parent = _mock_parent()
    parent.endpoints.get.return_value = {
        "endpoint": endpoint_payload(head_version=endpoint_version_payload(number=3))
    }

    endpoint = _ops(parent).get(TEST_ENDPOINT_ID)

    parent.endpoints.get.assert_called_once_with(TEST_ENDPOINT_ID)
    assert endpoint.head_version.version_number == 3
    assert endpoint.head_version.url == TEST_VERSION_MCP_URL


def test_get_without_live_version():
    parent = _mock_parent()
    parent.endpoints.get.return_value = {"endpoint": endpoint_payload()}

    endpoint = _ops(parent).get(TEST_ENDPOINT_ID)

    assert endpoint.head_version is None
    assert endpoint.version_mcp_url is None
    assert endpoint.url == TEST_ENDPOINT_MCP_URL


@pytest.mark.parametrize(
    "payload, expected",
    [({"is_default": True}, True), ({"is_default": False}, False), ({}, False)],
)
def test_get_reports_default_endpoint(payload, expected):
    parent = _mock_parent()
    parent.endpoints.get.return_value = {"endpoint": endpoint_payload(**payload)}

    endpoint = _ops(parent).get(TEST_ENDPOINT_ID)

    assert endpoint.is_default is expected


def test_list_passes_only_supplied_filters():
    parent = _mock_parent()
    parent.endpoints.list.return_value = {
        "endpoints": [endpoint_payload(head_version=endpoint_version_payload())],
        "next_page_token": "next",
    }

    page = _ops(parent).list(actor_id="actor-123", page_size=5)

    parent.endpoints.list.assert_called_once_with(actor_id="actor-123", page_size=5)
    assert page.next_page_token == "next"
    assert [endpoint.id for endpoint in page.endpoints] == [TEST_ENDPOINT_ID]
    assert page.endpoints[0].head_version.id == _VERSION_ID


def test_search_requires_query():
    parent = _mock_parent()
    parent.endpoints.list_search.return_value = {
        "endpoints": [],
        "next_page_token": "",
    }
    ops = _ops(parent)
    with pytest.raises(ValueError, match="query"):
        ops.search("")

    page = ops.search("support", page_token="t")

    parent.endpoints.list_search.assert_called_once_with(
        query="support", page_token="t"
    )
    assert page.endpoints == []
    assert page.next_page_token == ""


def test_update_requires_a_change():
    ops = _ops(_mock_parent())
    with pytest.raises(ValueError, match="name, insights"):
        ops.update(TEST_ENDPOINT_ID)


def test_update_patches_name_and_insights():
    parent = _mock_parent()
    parent.endpoints.patch.return_value = {"endpoint": endpoint_payload(name="renamed")}

    endpoint = _ops(parent).update(
        TEST_ENDPOINT_ID, name="renamed", insights={"traces": False}
    )

    parent.endpoints.patch.assert_called_once_with(
        TEST_ENDPOINT_ID, body={"name": "renamed", "insights": {"traces": False}}
    )
    assert endpoint.name == "renamed"


def test_deletes_delegate_to_generated_operations():
    parent = _mock_parent()
    ops = _ops(parent)

    assert ops.delete(TEST_ENDPOINT_ID) is None
    assert ops.delete_version(_VERSION_ID) is None

    parent.endpoints.delete.assert_called_once_with(TEST_ENDPOINT_ID)
    parent.endpoint_versions.delete.assert_called_once_with(_VERSION_ID)
    with pytest.raises(ValueError, match="version_id"):
        ops.delete_version("")


def test_create_version_returns_pinned_version():
    parent = _mock_parent()
    parent.endpoint_versions.create.return_value = endpoint_publish_response(number=2)

    version = _ops(parent).create_version(
        TEST_ENDPOINT_ID, actor_id="actor-123", tools=[]
    )

    parent.endpoint_versions.create.assert_called_once_with(
        TEST_ENDPOINT_ID,
        body={
            "actor_id": "actor-123",
            "policy": {"defaultAction": "ask"},
            "tools": [],
        },
    )
    assert version.id == f"{TEST_ENDPOINT_ID}.v2"
    assert version.endpoint_id == TEST_ENDPOINT_ID
    assert version.url == TEST_VERSION_MCP_URL
    assert version.tool_selection == {"references": []}


def test_promote_posts_version_id():
    parent = _mock_parent()
    parent.endpoint_versions.create_promotion.return_value = endpoint_publish_response(
        number=3, promoted_from=1
    )

    version = _ops(parent).promote(TEST_ENDPOINT_ID, _VERSION_ID)

    parent.endpoint_versions.create_promotion.assert_called_once_with(
        TEST_ENDPOINT_ID, body={"version_id": _VERSION_ID}
    )
    assert version.version_number == 3
    assert version.promoted_from_version_number == 1


def test_get_and_list_versions():
    parent = _mock_parent()
    parent.endpoint_versions.get.return_value = {"version": endpoint_version_payload()}
    parent.endpoint_versions.list.return_value = {
        "versions": [
            endpoint_version_payload(number=2),
            endpoint_version_payload(number=1),
        ],
        "next_page_token": "",
    }
    ops = _ops(parent)

    assert ops.get_version(_VERSION_ID).id == _VERSION_ID
    page = ops.list_versions(TEST_ENDPOINT_ID, page_size=2)

    parent.endpoint_versions.get.assert_called_once_with(_VERSION_ID)
    parent.endpoint_versions.list.assert_called_once_with(TEST_ENDPOINT_ID, page_size=2)
    assert [version.version_number for version in page.versions] == [2, 1]


def test_missing_generated_operations_raise_clear_error():
    parent = SimpleNamespace(_client=MagicMock())
    ops = EndpointsOperations(parent, gateway_endpoint=TEST_GATEWAY_URL)
    with pytest.raises(RuntimeError, match="upgrade pydo"):
        ops.get(TEST_ENDPOINT_ID)
    with pytest.raises(RuntimeError, match="upgrade pydo"):
        ops.get_version(_VERSION_ID)


def test_endpoint_tools_use_live_mcp_url_without_session_header():
    parent = _mock_parent(
        [
            FakeResponse(200, jsonrpc_result({"tools": _META_TOOL_DEFINITIONS})),
            FakeResponse(200, jsonrpc_result(call_result(structured={"ok": True}))),
        ]
    )
    parent.endpoints.create.return_value = endpoint_publish_response()
    endpoint = _ops(parent).create("support-agent", actor_id="actor-123")

    tools = endpoint.tools()
    messages = endpoint.handle_tool_calls(chat_tool_response())

    assert tools[0]["function"]["name"] == "action_search"
    for call in parent._client._pipeline.calls:
        assert call.request.url == TEST_ENDPOINT_MCP_URL
        assert call.request.headers[ACTOR_ID_HEADER] == "actor-123"
        assert SESSION_ID_HEADER not in call.request.headers
    assert _body(parent._client._pipeline.calls[1].request)["method"] == ("tools/call")
    assert messages[0]["role"] == "tool"


def test_version_tools_use_pinned_mcp_url():
    parent = _mock_parent(
        [FakeResponse(200, jsonrpc_result({"tools": _META_TOOL_DEFINITIONS}))]
    )
    parent.endpoints.create.return_value = endpoint_publish_response()
    version = _ops(parent).create("support-agent").head_version

    version.tools.list()

    assert parent._client._pipeline.calls[0].request.url == TEST_VERSION_MCP_URL


def test_endpoint_without_actor_sends_no_actor_header():
    parent = _mock_parent(
        [FakeResponse(200, jsonrpc_result({"tools": _META_TOOL_DEFINITIONS}))]
    )
    parent.endpoints.create.return_value = endpoint_publish_response(actor_id="")
    endpoint = _ops(parent).create("support-agent")

    endpoint.tools.list()

    request = parent._client._pipeline.calls[0].request
    assert ACTOR_ID_HEADER not in request.headers
    assert SESSION_ID_HEADER not in request.headers


def test_endpoint_approvals_use_endpoint_routes():
    parent = _mock_parent(
        [
            FakeResponse(200, {"status": "approved"}),
            FakeResponse(200, {"status": "denied"}),
        ]
    )
    parent.endpoints.create.return_value = endpoint_publish_response()
    endpoint = _ops(parent).create("support-agent", actor_id="actor-123")

    assert endpoint.approve("approval-123").status == "approved"
    assert endpoint.head_version.deny("approval-456").status == "denied"

    approve, deny = (call.request for call in parent._client._pipeline.calls)
    assert approve.url == (
        f"{TEST_GATEWAY_URL}/approvals/endpoint/{TEST_ENDPOINT_ID}/approval-123"
    )
    assert approve.headers[ACTOR_ID_HEADER] == "actor-123"
    assert _body(approve) == {"decision": "approve"}
    assert deny.url == (
        f"{TEST_GATEWAY_URL}/approvals/endpoint/{TEST_ENDPOINT_ID}"
        f"/version/{TEST_BACKING_SESSION_ID}/approval-456"
    )
    assert _body(deny) == {"decision": "deny"}


def test_endpoint_approval_url_keeps_prefix_and_quotes_id():
    url = _endpoint_approval_url(
        f"https://cloud.example/v2/action-gateway/api/mcp/endpoint/{TEST_ENDPOINT_ID}",
        "a/b",
    )
    assert url == (
        "https://cloud.example/v2/action-gateway/api/approvals/endpoint/"
        f"{TEST_ENDPOINT_ID}/a%2Fb"
    )
    with pytest.raises(GatewayProtocolError, match="endpoint MCP URL"):
        _endpoint_approval_url(f"{TEST_GATEWAY_URL}/mcp/session/abc", "a")


def test_endpoint_transport_requires_mcp_url():
    with pytest.raises(ValueError, match="mcp_url"):
        EndpointMCPTransport(MagicMock(), mcp_url="")


def test_action_gateway_client_exposes_endpoints():
    client = ActionGatewayClient(token="dummy")
    assert client.endpoints is client.gateway.endpoints
    assert client.endpoints_api is not client.endpoints
    assert {"endpoints", "endpoints_api", "endpoint_versions"} <= set(dir(client))


@requires_generated
def test_generated_create_posts_endpoint_body():
    parent = _generated_parent([FakeResponse(201, endpoint_publish_response())])

    endpoint = _ops(parent).create(
        "support-agent", actor_id="actor-123", tools=["exa_web_search@1"]
    )

    request = parent._client._pipeline.calls[0].request
    assert request.method == "POST"
    assert request.url.endswith("/v2/action-gateway/endpoints")
    assert _body(request) == {
        "name": "support-agent",
        "version": {
            "actor_id": "actor-123",
            "policy": {"defaultAction": "ask"},
            "tools": ["exa_web_search@1"],
        },
    }
    assert endpoint.url == TEST_ENDPOINT_MCP_URL


@requires_generated
def test_generated_list_sends_query_parameters():
    parent = _generated_parent(
        [FakeResponse(200, {"endpoints": [], "next_page_token": ""})]
    )

    _ops(parent).list(name="support-agent", page_token="abc")

    request = parent._client._pipeline.calls[0].request
    url = urlsplit(request.url)
    assert url.path == "/v2/action-gateway/endpoints"
    assert parse_qs(url.query) == {
        "name": ["support-agent"],
        "page_token": ["abc"],
        "page_size": ["20"],
    }


@requires_generated
def test_generated_version_routes():
    parent = _generated_parent(
        [
            FakeResponse(201, endpoint_publish_response(number=2, promoted_from=1)),
            FakeResponse(200, {"version": endpoint_version_payload()}),
            FakeResponse(204),
        ]
    )
    ops = _ops(parent)

    ops.promote(TEST_ENDPOINT_ID, _VERSION_ID)
    ops.get_version(_VERSION_ID)
    ops.delete_version(_VERSION_ID)

    promote, get, delete = (call.request for call in parent._client._pipeline.calls)
    assert promote.method == "POST"
    assert promote.url.endswith(
        f"/v2/action-gateway/endpoints/{TEST_ENDPOINT_ID}/versions:promote"
    )
    assert _body(promote) == {"version_id": _VERSION_ID}
    assert get.url.endswith(f"/v2/action-gateway/endpoint-versions/{_VERSION_ID}")
    assert delete.method == "DELETE"
    assert delete.url == get.url
