# pylint: disable=missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :mod:`pydo.gateway.providers` and ``handle_tool_calls``."""

from __future__ import annotations

import json

import pytest

from pydo.custom_extensions import _wrap
from pydo.gateway import (
    ChatCompletionsProvider,
    MessagesProvider,
    ResponsesProvider,
    normalize_invoke_arguments,
    simplify_messages_input_schema,
)

from .conftest import (
    FakeResponse,
    call_result,
    jsonrpc_result,
    make_gateway,
    sent_payload,
)

_CATALOG = [
    {
        "name": "web_search",
        "title": "Web Search",
        "description": "Search the public web",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    }
]

_META_TOOLS = [
    {
        "name": "action_search",
        "description": "Find tools",
        "inputSchema": {"type": "object"},
    },
    {
        "name": "action_invoke",
        "description": "Run tools",
        "inputSchema": {"type": "object"},
    },
    {
        "name": "action_code",
        "description": "Run code",
        "inputSchema": {"type": "object"},
    },
]


# -- wrap_tools ---------------------------------------------------------------


def test_chat_completions_wrap_tools():
    tools = ChatCompletionsProvider().wrap_tools(_CATALOG)
    assert tools == [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the public web",
                "parameters": _CATALOG[0]["inputSchema"],
            },
        }
    ]


def test_messages_wrap_tools():
    tools = MessagesProvider().wrap_tools(_CATALOG)
    assert tools == [
        {
            "name": "web_search",
            "description": "Search the public web",
            "input_schema": _CATALOG[0]["inputSchema"],
        }
    ]


def test_messages_wrap_tools_preserves_meta_tool_names():
    tools = MessagesProvider().wrap_tools(_META_TOOLS)
    assert [tool["name"] for tool in tools] == [
        "action_search",
        "action_invoke",
        "action_code",
    ]


def test_simplify_messages_input_schema_strips_top_level_any_of():
    schema = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "code_to_execute": {"type": "string"},
        },
        "anyOf": [
            {"required": ["code"]},
            {"required": ["code_to_execute"]},
        ],
    }
    simplified = simplify_messages_input_schema(schema)
    assert "anyOf" not in simplified
    assert simplified["properties"]["code"]["type"] == "string"


def test_chat_completions_wrap_tools_strips_any_of_from_code_meta_tool():
    tools = ChatCompletionsProvider().wrap_tools(
        [
            {
                "name": "action_code",
                "description": "Run Python",
                "inputSchema": {
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "anyOf": [{"required": ["code"]}],
                },
            }
        ]
    )
    assert tools[0]["function"]["name"] == "action_code"
    assert "anyOf" not in tools[0]["function"]["parameters"]


def test_responses_wrap_tools_preserves_meta_tool_names():
    tools = ResponsesProvider().wrap_tools(_META_TOOLS)
    assert [tool["name"] for tool in tools] == [
        "action_search",
        "action_invoke",
        "action_code",
    ]


def test_responses_wrap_tools():
    tools = ResponsesProvider().wrap_tools(_CATALOG)
    assert tools == [
        {
            "type": "function",
            "name": "web_search",
            "description": "Search the public web",
            "parameters": _CATALOG[0]["inputSchema"],
        }
    ]


def test_wrap_tools_falls_back_to_title_and_empty_schema():
    tools = ChatCompletionsProvider().wrap_tools([{"name": "t", "title": "T"}])
    function = tools[0]["function"]
    assert function["description"] == "T"
    assert function["parameters"] == {"type": "object", "properties": {}}


# -- extract_tool_calls -------------------------------------------------------


def _chat_response(arguments='{"query": "do"}'):
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "web_search",
                                "arguments": arguments,
                            },
                        }
                    ],
                }
            }
        ]
    }


def _messages_response():
    return {
        "content": [
            {"type": "text", "text": "let me check"},
            {
                "type": "tool_use",
                "id": "toolu_1",
                "name": "web_search",
                "input": {"query": "do"},
            },
        ]
    }


def _responses_response():
    return {
        "output": [
            {
                "type": "function_call",
                "call_id": "fc_1",
                "name": "web_search",
                "arguments": '{"query": "do"}',
            }
        ]
    }


@pytest.mark.parametrize("wrap", [lambda x: x, _wrap], ids=["dict", "DotDict"])
def test_chat_completions_extract(wrap):
    calls = ChatCompletionsProvider().extract_tool_calls(wrap(_chat_response()))
    assert len(calls) == 1
    assert calls[0].call_id == "call_1"
    assert calls[0].name == "web_search"
    assert calls[0].arguments == {"query": "do"}


@pytest.mark.parametrize("wrap", [lambda x: x, _wrap], ids=["dict", "DotDict"])
def test_messages_extract(wrap):
    calls = MessagesProvider().extract_tool_calls(wrap(_messages_response()))
    assert len(calls) == 1
    assert calls[0].call_id == "toolu_1"
    assert calls[0].arguments == {"query": "do"}


@pytest.mark.parametrize("wrap", [lambda x: x, _wrap], ids=["dict", "DotDict"])
def test_responses_extract(wrap):
    calls = ResponsesProvider().extract_tool_calls(wrap(_responses_response()))
    assert len(calls) == 1
    assert calls[0].call_id == "fc_1"
    assert calls[0].arguments == {"query": "do"}


def test_extract_returns_empty_without_tool_calls():
    assert (
        ChatCompletionsProvider().extract_tool_calls(
            {"choices": [{"message": {"content": "hi"}}]}
        )
        == []
    )
    assert MessagesProvider().extract_tool_calls({"content": []}) == []
    assert ResponsesProvider().extract_tool_calls({"output": []}) == []


# -- format_tool_results ------------------------------------------------------


def test_format_results_per_provider():
    provider = ChatCompletionsProvider()
    calls = provider.extract_tool_calls(_chat_response())
    messages = provider.format_tool_results(calls, [{"answer": 1}])
    assert messages == [
        {"role": "tool", "tool_call_id": "call_1", "content": '{"answer": 1}'}
    ]

    provider = MessagesProvider()
    calls = provider.extract_tool_calls(_messages_response())
    messages = provider.format_tool_results(calls, [{"answer": 1}])
    assert messages[0]["role"] == "user"
    assert messages[0]["content"][0]["type"] == "tool_result"
    assert messages[0]["content"][0]["tool_use_id"] == "toolu_1"

    provider = ResponsesProvider()
    calls = provider.extract_tool_calls(_responses_response())
    items = provider.format_tool_results(calls, [{"answer": 1}])
    assert items == [
        {
            "type": "function_call_output",
            "call_id": "fc_1",
            "output": '{"answer": 1}',
        }
    ]


# -- tools() callable ---------------------------------------------------------


def test_tools_callable_wraps_meta_tools_by_default():
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result({"tools": _META_TOOLS}))],
        provider=ChatCompletionsProvider(),
    )
    tools = gateway.tools()
    assert [t["function"]["name"] for t in tools] == [
        "action_search",
        "action_invoke",
        "action_code",
    ]


def test_tools_callable_wraps_meta_tools_for_messages():
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result({"tools": _META_TOOLS}))],
        provider=MessagesProvider(),
    )
    tools = gateway.tools()
    assert [t["name"] for t in tools] == [
        "action_search",
        "action_invoke",
        "action_code",
    ]


def test_tools_callable_include_all_wraps_catalog():
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result({"tools": _CATALOG}))],
        provider=ChatCompletionsProvider(),
    )
    tools = gateway.tools(include_all=True)
    assert tools[0]["function"]["name"] == "web_search"


def test_tools_callable_names_filter_and_missing():
    gateway = make_gateway(
        [
            FakeResponse(200, jsonrpc_result({"tools": _CATALOG})),
            FakeResponse(200, jsonrpc_result({"tools": _CATALOG})),
        ],
        provider=ChatCompletionsProvider(),
    )
    tools = gateway.tools(names=["web_search"])
    assert len(tools) == 1
    with pytest.raises(LookupError, match="nope"):
        gateway.tools(names=["nope"])


def test_tools_callable_via_search():
    search_payload = {
        "results": [
            {
                "index": 1,
                "use_case": "web",
                "results": [_CATALOG[0], _CATALOG[0]],  # dupes collapse
            }
        ]
    }
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result(call_result(search_payload)))],
        provider=ChatCompletionsProvider(),
    )
    tools = gateway.tools(search="search the web", limit=2)
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "web_search"


# -- handle_tool_calls --------------------------------------------------------


def test_handle_tool_calls_batches_concrete_tools():
    envelope = {
        "total_count": 1,
        "success_count": 1,
        "error_count": 0,
        "results": [
            {
                "index": 0,
                "tool": "web_search",
                "result": {"status": "succeeded", "output": {"answer": 42}},
            }
        ],
    }
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result(call_result(envelope)))],
        provider=ChatCompletionsProvider(),
    )
    messages = gateway.handle_tool_calls(_chat_response(), rationale="why not")

    params = sent_payload(gateway)["params"]
    assert params["name"] == "action_invoke"
    assert params["arguments"]["rationale"] == "why not"
    assert params["arguments"]["tools"] == [
        {"tool": "web_search", "arguments": {"query": "do"}}
    ]

    assert messages[0]["role"] == "tool"
    assert messages[0]["tool_call_id"] == "call_1"
    assert json.loads(messages[0]["content"]) == {"answer": 42}


def test_normalize_invoke_arguments_accepts_chat_function_shape():
    arguments = normalize_invoke_arguments(
        {
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "arguments": '{"query": "digitalocean news"}',
                    },
                }
            ]
        }
    )
    assert arguments["tools"] == [
        {"tool": "web_search", "arguments": {"query": "digitalocean news"}}
    ]


def test_handle_tool_calls_normalizes_action_invoke_payload():
    envelope = {
        "total_count": 1,
        "success_count": 1,
        "error_count": 0,
        "results": [
            {
                "index": 0,
                "tool": "web_search",
                "result": {"status": "succeeded", "output": {"answer": 1}},
            }
        ],
    }
    gateway = make_gateway(
        [
            FakeResponse(200, jsonrpc_result({"tools": _META_TOOLS})),
            FakeResponse(200, jsonrpc_result(call_result(envelope))),
        ],
        provider=ChatCompletionsProvider(),
    )
    gateway.tools()
    response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_invoke",
                            "function": {
                                "name": "action_invoke",
                                "arguments": json.dumps(
                                    {
                                        "tools": [
                                            {
                                                "function": {
                                                    "name": "web_search",
                                                    "arguments": {
                                                        "query": "digitalocean"
                                                    },
                                                }
                                            }
                                        ]
                                    }
                                ),
                            },
                        }
                    ]
                }
            }
        ]
    }
    messages = gateway.handle_tool_calls(response)
    params = sent_payload(gateway, 1)["params"]
    assert params["name"] == "action_invoke"
    assert params["arguments"]["tools"] == [
        {"tool": "web_search", "arguments": {"query": "digitalocean"}}
    ]
    assert json.loads(messages[0]["content"]) == envelope


def test_handle_tool_calls_routes_meta_tools_directly():
    gateway = make_gateway(
        [
            FakeResponse(200, jsonrpc_result({"tools": _META_TOOLS})),
            FakeResponse(200, jsonrpc_result(call_result({"results": []}))),
        ],
        provider=ChatCompletionsProvider(),
    )
    gateway.tools()
    response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_meta",
                            "function": {
                                "name": "action_search",
                                "arguments": '{"queries": [{"use_case": "x"}]}',
                            },
                        }
                    ]
                }
            }
        ]
    }
    messages = gateway.handle_tool_calls(response)
    params = sent_payload(gateway, 1)["params"]
    assert params["name"] == "action_search"
    assert json.loads(messages[0]["content"]) == {"results": []}


def test_handle_tool_calls_surfaces_failures_as_content():
    envelope = {
        "total_count": 1,
        "success_count": 0,
        "error_count": 1,
        "results": [
            {
                "index": 0,
                "tool": "web_search",
                "result": {
                    "status": "failed",
                    "error": {"class": "timeout", "message": "too slow"},
                },
            }
        ],
    }
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result(call_result(envelope)))],
        provider=ChatCompletionsProvider(),
    )
    messages = gateway.handle_tool_calls(_chat_response())
    content = json.loads(messages[0]["content"])
    assert content["error"]["class"] == "timeout"


def test_handle_tool_calls_no_calls_returns_empty():
    gateway = make_gateway([], provider=ChatCompletionsProvider())
    assert gateway.handle_tool_calls({"choices": [{"message": {}}]}) == []


def test_tools_callable_requires_provider():
    gateway = make_gateway([], provider=None)
    gateway.tools._provider = None
    with pytest.raises(RuntimeError, match="provider"):
        gateway.tools()
