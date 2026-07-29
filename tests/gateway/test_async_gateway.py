# pylint: disable=missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async smoke tests for :mod:`pydo.aio.gateway`."""

from __future__ import annotations

import asyncio
import json

import pytest
from azure.core.exceptions import HttpResponseError

from pydo.aio.gateway import (
    AsyncGatewayResources,
    AsyncMCPTransport,
    AsyncSessionsOperations,
)
from pydo.custom_extensions import _BaseURLProxy
from pydo.gateway import (
    ACTOR_ID_HEADER,
    SESSION_ID_HEADER,
    ChatCompletionsProvider,
    GatewayToolError,
)

from .conftest import (
    TEST_GATEWAY_URL,
    TEST_SESSION_URN,
    AsyncFakeResponse,
    jsonrpc_result,
    chat_tool_response,
    invoke_envelope,
    make_async_gateway,
    make_async_parent,
    session_create_response,
    tool_result,
)


def _run(coro):
    return asyncio.run(coro)


def _sent_request(gateway, index=0):
    pipeline = gateway._transport._client._original._pipeline
    return pipeline.calls[index].request


def _sent_payload(gateway, index=0):
    content = _sent_request(gateway, index).content
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    return json.loads(content)


def test_list_defaults_to_meta():
    gateway = make_async_gateway([])
    tools = _run(gateway.tools.list())
    assert [t.name for t in tools] == [
        "action_search",
        "action_invoke",
        "action_code",
    ]


def test_invoke_and_invoke_one():
    envelope = invoke_envelope(output={"answer": 7})
    gateway = make_async_gateway([AsyncFakeResponse(200, envelope)])
    output = _run(gateway.tools.invoke_one("web_search", {"query": "do"}))
    assert output.answer == 7
    request = _sent_request(gateway)
    assert request.url.endswith("/tools/invoke")
    assert request.headers[SESSION_ID_HEADER] == "test-session"
    assert request.headers[ACTOR_ID_HEADER] == "actor-123"
    assert _sent_payload(gateway)["tools"][0]["tool"] == "web_search"


def test_code_execute_failure_raises():
    gateway = make_async_gateway(
        [
            AsyncFakeResponse(
                200,
                tool_result(error={"class": "execution_failed", "message": "crash"}),
            )
        ]
    )
    with pytest.raises(GatewayToolError, match="crash"):
        _run(gateway.code.execute("1/0"))


def test_http_error_reads_async_response_once():
    response = AsyncFakeResponse(400, "bad request")
    gateway = make_async_gateway([response])
    with pytest.raises(HttpResponseError, match="bad request"):
        _run(gateway.tools.list(include_all=True))
    assert response.read_calls == 1


def test_mcp_transport_parses_sse_response():
    response = (
        "event: message\n"
        'data: {"jsonrpc":"2.0","id":1,"result":{"tools":'
        '[{"name":"action_search"}]}}\n\n'
    )
    parent = make_async_parent([AsyncFakeResponse(200, response)])
    proxy = _BaseURLProxy(parent._client, TEST_GATEWAY_URL)
    gateway = AsyncGatewayResources(
        parent,
        gateway_endpoint=TEST_GATEWAY_URL,
        transport=AsyncMCPTransport(
            proxy, session_id=TEST_SESSION_URN, actor_id="actor-123"
        ),
    )
    assert _run(gateway.tools.list())[0].name == "action_search"


def test_session_create_uses_public_api_and_actor_header():
    parent = make_async_parent(
        [
            AsyncFakeResponse(200, session_create_response()),
            AsyncFakeResponse(200, jsonrpc_result({"tools": []})),
        ]
    )
    operations = AsyncSessionsOperations(parent, gateway_endpoint=TEST_GATEWAY_URL)

    async def scenario():
        session = await operations.create(
            "actor-123",
            name="named",
            tools=["web_search@v1"],
            config={"preloadTools": ["web_search@v1"]},
        )
        await session.tools.list(include_all=True)
        return session

    session = _run(scenario())
    create_request = parent._client._pipeline.calls[0].request
    assert create_request.url.endswith("/v2/action-gateway/sessions")
    assert json.loads(create_request.content) == {
        "actor_id": "actor-123",
        "name": "named",
        "policy": {"defaultAction": "ask"},
        "tools": ["web_search@v1"],
        "config": {"preloadTools": ["web_search@v1"]},
    }
    tool_request = parent._client._pipeline.calls[1].request
    assert tool_request.url == session.url
    assert tool_request.headers[SESSION_ID_HEADER] == "test-session"
    assert tool_request.headers[ACTOR_ID_HEADER] == "actor-123"
    assert session.actor_id == "actor-123"
    assert session.selected_tools == []


def test_session_approve_posts_to_gateway():
    parent = make_async_parent(
        [
            AsyncFakeResponse(200, session_create_response()),
            AsyncFakeResponse(200, {"status": "approved"}),
        ]
    )
    operations = AsyncSessionsOperations(parent, gateway_endpoint=TEST_GATEWAY_URL)

    async def scenario():
        session = await operations.create("actor-123")
        result = await session.approve("approval-123")
        return session, result

    session, result = _run(scenario())
    request = parent._client._pipeline.calls[1].request
    assert request.url == f"{TEST_GATEWAY_URL}/approvals/approval-123"
    assert request.headers[SESSION_ID_HEADER] == "test-session"
    assert request.headers[ACTOR_ID_HEADER] == "actor-123"
    assert json.loads(request.content) == {"decision": "approve"}
    assert result.status == "approved"
    assert session.actor_id == "actor-123"


def test_session_deny_posts_to_gateway():
    parent = make_async_parent(
        [
            AsyncFakeResponse(200, session_create_response()),
            AsyncFakeResponse(200, {"status": "denied"}),
        ]
    )
    operations = AsyncSessionsOperations(parent, gateway_endpoint=TEST_GATEWAY_URL)

    async def scenario():
        session = await operations.create("actor-123")
        return await session.deny("approval-123")

    result = _run(scenario())
    request = parent._client._pipeline.calls[1].request
    assert json.loads(request.content) == {"decision": "deny"}
    assert result.status == "denied"


def test_tools_callable_and_handle_tool_calls():
    envelope = invoke_envelope(output={"ok": True})
    gateway = make_async_gateway(
        [AsyncFakeResponse(200, envelope)],
        provider=ChatCompletionsProvider(),
    )

    async def scenario():
        tools = await gateway.tools()
        messages = await gateway.handle_tool_calls(chat_tool_response())
        return tools, messages

    tools, messages = _run(scenario())
    assert [t["function"]["name"] for t in tools] == [
        "action_search",
        "action_invoke",
        "action_code",
    ]
    assert messages[0]["role"] == "tool"
    assert json.loads(messages[0]["content"]) == {"ok": True}
