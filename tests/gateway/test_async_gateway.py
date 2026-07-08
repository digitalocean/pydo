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

from pydo.gateway import ChatCompletionsProvider, GatewayToolError

from .conftest import (
    AsyncFakeResponse,
    call_result,
    jsonrpc_result,
    make_async_gateway,
)


def _run(coro):
    return asyncio.run(coro)


def _sent_payload(gateway, index=0):
    pipeline = gateway._transport._client._original._pipeline
    content = pipeline.calls[index].request.content
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    return json.loads(content)


def test_list_defaults_to_meta():
    gateway = make_async_gateway(
        [AsyncFakeResponse(200, jsonrpc_result({"tools": [{"name": "action.search"}]}))]
    )
    tools = _run(gateway.tools.list())
    assert tools[0].name == "action.search"
    pipeline = gateway._transport._client._original._pipeline
    assert pipeline.calls[0].request.url.endswith("/mcp/meta")


def test_invoke_and_invoke_one():
    envelope = {
        "total_count": 1,
        "success_count": 1,
        "error_count": 0,
        "results": [
            {
                "index": 0,
                "tool": "web_search",
                "result": {"status": "succeeded", "output": {"answer": 7}},
            }
        ],
    }
    gateway = make_async_gateway(
        [AsyncFakeResponse(200, jsonrpc_result(call_result(envelope)))]
    )
    output = _run(gateway.tools.invoke_one("web_search", {"query": "do"}))
    assert output.answer == 7
    params = _sent_payload(gateway)["params"]
    assert params["name"] == "action.invoke"


def test_code_execute_failure_raises():
    structured = {"error": {"class": "execution_failed", "message": "crash"}}
    gateway = make_async_gateway(
        [AsyncFakeResponse(200, jsonrpc_result(call_result(structured, is_error=True)))]
    )
    with pytest.raises(GatewayToolError, match="crash"):
        _run(gateway.code.execute("1/0"))


def test_tools_callable_and_handle_tool_calls():
    meta_tools = [
        {
            "name": "action.search",
            "description": "d",
            "inputSchema": {"type": "object"},
        },
        {
            "name": "action.invoke",
            "description": "d",
            "inputSchema": {"type": "object"},
        },
        {"name": "action.code", "description": "d", "inputSchema": {"type": "object"}},
    ]
    envelope = {
        "total_count": 1,
        "success_count": 1,
        "error_count": 0,
        "results": [
            {
                "index": 0,
                "tool": "web_search",
                "result": {"status": "succeeded", "output": {"ok": True}},
            }
        ],
    }
    gateway = make_async_gateway(
        [
            AsyncFakeResponse(200, jsonrpc_result({"tools": meta_tools})),
            AsyncFakeResponse(200, jsonrpc_result(call_result(envelope))),
        ],
        provider=ChatCompletionsProvider(),
    )

    async def scenario():
        tools = await gateway.tools()
        response = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "web_search",
                                    "arguments": '{"query": "do"}',
                                },
                            }
                        ]
                    }
                }
            ]
        }
        messages = await gateway.handle_tool_calls(response)
        return tools, messages

    tools, messages = _run(scenario())
    assert [t["function"]["name"] for t in tools] == [
        "action.search",
        "action.invoke",
        "action.code",
    ]
    assert messages[0]["role"] == "tool"
    assert json.loads(messages[0]["content"]) == {"ok": True}
