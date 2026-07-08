# pylint: disable=missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :class:`pydo.gateway.custom_operations.CodeOperations`."""

from __future__ import annotations

import pytest

from pydo.gateway import GatewayToolError

from .conftest import (
    FakeResponse,
    call_result,
    jsonrpc_result,
    make_gateway,
    sent_payload,
    sent_request,
)


def test_execute_happy_path():
    output = {"stdout": "hello\n", "stderr": "", "exit_code": 0}
    gateway = make_gateway([FakeResponse(200, jsonrpc_result(call_result(output)))])
    result = gateway.code.execute("print('hello')", thought="say hello")

    request = sent_request(gateway)
    assert request.url.endswith("/mcp/meta")
    params = sent_payload(gateway)["params"]
    assert params["name"] == "action_code"
    assert params["arguments"] == {
        "code": "print('hello')",
        "thought": "say hello",
    }

    assert result.stdout == "hello\n"
    assert result.exit_code == 0


def test_execute_omits_empty_thought():
    output = {"stdout": "", "stderr": "", "exit_code": 0}
    gateway = make_gateway([FakeResponse(200, jsonrpc_result(call_result(output)))])
    gateway.code.execute("pass")
    assert "thought" not in sent_payload(gateway)["params"]["arguments"]


def test_execute_rejects_empty_code():
    gateway = make_gateway([])
    with pytest.raises(ValueError, match="empty"):
        gateway.code.execute("   ")


def test_execute_sandbox_failure_raises():
    structured = {
        "error": {
            "class": "execution_failed",
            "message": "sandbox crashed",
            "retriable": False,
        }
    }
    gateway = make_gateway(
        [FakeResponse(200, jsonrpc_result(call_result(structured, is_error=True)))]
    )
    with pytest.raises(GatewayToolError, match="sandbox crashed") as excinfo:
        gateway.code.execute("1/0")
    assert excinfo.value.error_class == "execution_failed"
