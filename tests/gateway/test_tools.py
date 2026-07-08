# pylint: disable=missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :class:`pydo.gateway.custom_operations.ToolsOperations`."""

from __future__ import annotations

import pytest

from pydo.gateway import GatewayToolError

from .conftest import (
    FakeResponse,
    call_result,
    jsonrpc_result,
    make_gateway,
    sent_payload,
)

_SEARCH_PAYLOAD = {
    "results": [
        {
            "index": 1,
            "use_case": "search the web",
            "results": [
                {
                    "name": "web_search",
                    "title": "Web Search",
                    "description": "Search the public web",
                    "inputSchema": {"type": "object"},
                    "score": 12.3,
                }
            ],
        }
    ]
}


def _invoke_envelope(results):
    return {
        "total_count": len(results),
        "success_count": sum(
            1 for r in results if r["result"].get("status") == "succeeded"
        ),
        "error_count": sum(
            1 for r in results if r["result"].get("status") != "succeeded"
        ),
        "results": results,
    }


# -- search ------------------------------------------------------------------


def test_search_accepts_single_string():
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result(call_result(_SEARCH_PAYLOAD)))]
    )
    result = gateway.tools.search("search the web")

    params = sent_payload(gateway)["params"]
    assert params["name"] == "action.search"
    assert params["arguments"]["queries"] == [{"use_case": "search the web"}]
    assert result.results[0].results[0].name == "web_search"


def test_search_accepts_dicts_and_filters():
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result(call_result(_SEARCH_PAYLOAD)))]
    )
    gateway.tools.search(
        [
            {"use_case": "find stuff", "known_fields": "site:example.com"},
            "another use case",
        ],
        providers=["exa"],
        tags=["web"],
        limit=3,
    )
    arguments = sent_payload(gateway)["params"]["arguments"]
    assert arguments["queries"] == [
        {"use_case": "find stuff", "known_fields": "site:example.com"},
        {"use_case": "another use case"},
    ]
    assert arguments["providers"] == ["exa"]
    assert arguments["tags"] == ["web"]
    assert arguments["limit"] == 3


def test_search_rejects_missing_use_case_and_bad_counts():
    gateway = make_gateway([])
    with pytest.raises(ValueError, match="use_case"):
        gateway.tools.search([{"known_fields": "x"}])
    with pytest.raises(ValueError, match="between 1 and 5"):
        gateway.tools.search(["a", "b", "c", "d", "e", "f"])
    with pytest.raises(TypeError):
        gateway.tools.search([42])


# -- invoke ------------------------------------------------------------------


def test_invoke_shapes_arguments_and_returns_envelope():
    envelope = _invoke_envelope(
        [
            {
                "index": 0,
                "tool": "web_search",
                "result": {"status": "succeeded", "output": {"answer": 1}},
            },
            {
                "index": 1,
                "tool": "missing_tool",
                "result": {
                    "status": "failed",
                    "error": {"class": "invalid_argument", "message": "unknown tool"},
                },
            },
        ]
    )
    gateway = make_gateway([FakeResponse(200, jsonrpc_result(call_result(envelope)))])
    result = gateway.tools.invoke(
        [
            {"tool": "web_search", "arguments": {"query": "do"}},
            {"tool_slug": "missing_tool"},
        ],
        rationale="testing",
    )

    params = sent_payload(gateway)["params"]
    assert params["name"] == "action.invoke"
    assert params["arguments"]["rationale"] == "testing"
    assert params["arguments"]["tools"] == [
        {"tool": "web_search", "arguments": {"query": "do"}},
        {"tool": "missing_tool", "arguments": {}},
    ]

    # per-item failures stay in the envelope — no raise
    assert result.error_count == 1
    assert result.results[1].result.status == "failed"


def test_invoke_validates_counts_and_entries():
    gateway = make_gateway([])
    with pytest.raises(ValueError, match="between 1 and 10"):
        gateway.tools.invoke([])
    with pytest.raises(ValueError, match="between 1 and 10"):
        gateway.tools.invoke([{"tool": f"t{i}", "arguments": {}} for i in range(11)])
    with pytest.raises(ValueError, match="'tool' name"):
        gateway.tools.invoke([{"arguments": {}}])
    with pytest.raises(TypeError):
        gateway.tools.invoke(["web_search"])


def test_invoke_one_returns_output():
    envelope = _invoke_envelope(
        [
            {
                "index": 0,
                "tool": "web_search",
                "result": {"status": "succeeded", "output": {"answer": 42}},
            }
        ]
    )
    gateway = make_gateway([FakeResponse(200, jsonrpc_result(call_result(envelope)))])
    output = gateway.tools.invoke_one("web_search", {"query": "do"})
    assert output.answer == 42


def test_invoke_one_raises_on_failure():
    envelope = _invoke_envelope(
        [
            {
                "index": 0,
                "tool": "web_search",
                "result": {
                    "status": "failed",
                    "error": {
                        "class": "upstream_error",
                        "message": "exa is down",
                        "retriable": True,
                    },
                },
                "invocation_id": "inv_9",
            }
        ]
    )
    gateway = make_gateway([FakeResponse(200, jsonrpc_result(call_result(envelope)))])
    with pytest.raises(GatewayToolError, match="exa is down") as excinfo:
        gateway.tools.invoke_one("web_search", {"query": "do"})
    assert excinfo.value.error_class == "upstream_error"
    assert excinfo.value.retriable is True


# -- concrete call -----------------------------------------------------------


def test_call_hits_concrete_endpoint():
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result(call_result({"provider": "exa"})))]
    )
    result = gateway.tools.call("web_search", {"query": "do"})
    payload = sent_payload(gateway)
    assert payload["params"]["name"] == "web_search"
    assert result.provider == "exa"
