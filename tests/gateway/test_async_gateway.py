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

from pydo.aio.gateway import AsyncGatewayResources, AsyncMCPTransport
from pydo.custom_extensions import _BaseURLProxy
from pydo.gateway import ChatCompletionsProvider, GatewayToolError, SESSION_ID_HEADER

from .conftest import (
    TEST_GATEWAY_URL,
    TEST_SESSION_URN,
    AsyncFakeResponse,
    chat_tool_response,
    invoke_envelope,
    make_async_gateway,
    make_async_parent,
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
    assert request.headers[SESSION_ID_HEADER] == TEST_SESSION_URN
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
        transport=AsyncMCPTransport(proxy, session_id=TEST_SESSION_URN),
    )
    assert _run(gateway.tools.list())[0].name == "action_search"


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
