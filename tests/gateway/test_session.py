# pylint: disable=missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for Action Gateway sessions."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from azure.core.exceptions import ResourceNotFoundError

from pydo.gateway import (
    ACTOR_ID_HEADER,
    SESSION_ID_HEADER,
    SessionsOperations,
    normalize_permissions,
)
from pydo.gateway.transport import _META_TOOL_DEFINITIONS

from .conftest import (
    TEST_GATEWAY_URL,
    TEST_SESSION_URN,
    FakeResponse,
    call_result,
    chat_tool_response,
    jsonrpc_result,
    make_parent,
    session_create_response,
)


def test_normalize_permissions_defaults_to_ask():
    assert normalize_permissions(None) == {"defaultAction": "ask"}


def test_normalize_permissions_accepts_snake_case():
    policy = normalize_permissions(
        {
            "default_action": "ask",
            "rules": [
                {"tool": "toolbelt:read-only@1.2.3", "action": "allow"},
                {"tool": "gmail", "action": "deny"},
            ],
        }
    )
    assert policy == {
        "defaultAction": "ask",
        "rules": [
            {"tool": "toolbelt:read-only@1.2.3", "action": "allow"},
            {"tool": "gmail", "action": "deny"},
        ],
    }


def test_normalize_permissions_requires_tool():
    with pytest.raises(ValueError, match="requires tool"):
        normalize_permissions({"rules": [{"action": "allow"}]})


def test_normalize_permissions_rejects_legacy_toolbelt_key():
    with pytest.raises(ValueError, match="toolbelt permissions are no longer"):
        normalize_permissions({"rules": [{"toolbelt": "read-only@1.2.3"}]})


def test_sessions_create_requires_actor_id():
    ops = SessionsOperations(make_parent([]), gateway_endpoint=TEST_GATEWAY_URL)
    with pytest.raises(ValueError, match="actor_id"):
        ops.create("")


def test_sessions_create_404_uses_generated_error_mapping():
    response = FakeResponse(
        404,
        {"id": "not_found", "message": "Your request could not be routed."},
    )
    response.request = SimpleNamespace(
        url="https://api.digitalocean.com/v2/action-gateway/sessions"
    )
    ops = SessionsOperations(make_parent([response]), gateway_endpoint=TEST_GATEWAY_URL)
    with pytest.raises(ResourceNotFoundError):
        ops.create("user-123")


def test_sessions_create_posts_to_do_api_and_binds_returned_mcp_url():
    parent = make_parent(
        [
            FakeResponse(200, session_create_response()),
            FakeResponse(200, jsonrpc_result({"tools": _META_TOOL_DEFINITIONS})),
            FakeResponse(200, jsonrpc_result(call_result(structured={"ok": True}))),
        ]
    )
    ops = SessionsOperations(parent, gateway_endpoint=TEST_GATEWAY_URL)
    session = ops.create("user-123")

    create_req = parent._client._pipeline.calls[0].request
    assert create_req.method == "POST"
    assert create_req.url.endswith("/v2/action-gateway/sessions")
    body = json.loads(create_req.content)
    assert body["actor_id"] == "user-123"
    assert "end_user_id" not in body
    assert body["policy"] == {"defaultAction": "ask"}
    assert body["name"].startswith("pydo-session-")

    assert session.session_urn == TEST_SESSION_URN
    assert session.actor_id == "user-123"
    assert session.url == "https://actions.do-ai-test.run/mcp/session/test-session"

    tools = session.tools()
    assert [t["function"]["name"] for t in tools][:1] == ["action_search"]

    messages = session.handle_tool_calls(chat_tool_response())
    invoke_req = parent._client._pipeline.calls[2].request
    assert invoke_req.url == session.url
    assert invoke_req.headers[SESSION_ID_HEADER] == "test-session"
    assert invoke_req.headers[ACTOR_ID_HEADER] == "user-123"
    assert json.loads(invoke_req.content)["method"] == "tools/call"
    assert messages[0]["role"] == "tool"


def test_sessions_create_with_permissions_and_name():
    parent = make_parent(
        [
            FakeResponse(
                200,
                session_create_response(name="named"),
            )
        ]
    )
    ops = SessionsOperations(parent, gateway_endpoint=TEST_GATEWAY_URL)
    session = ops.create(
        "u1",
        name="named",
        permissions={
            "default_action": "deny",
            "rules": [{"tool": "web_search", "action": "allow"}],
        },
    )
    body = json.loads(parent._client._pipeline.calls[0].request.content)
    assert body["name"] == "named"
    assert body["policy"] == {
        "defaultAction": "deny",
        "rules": [{"tool": "web_search", "action": "allow"}],
    }
    assert session.name == "named"


def test_sessions_create_sends_tool_selection_and_config():
    parent = make_parent([FakeResponse(200, session_create_response())])
    session = SessionsOperations(parent, gateway_endpoint=TEST_GATEWAY_URL).create(
        "u1",
        tools=["web_search@v1", "toolbelt:read-only@2"],
        config={"preloadTools": ["web_search@v1"]},
    )

    body = json.loads(parent._client._pipeline.calls[0].request.content)
    assert body["tools"] == ["web_search@v1", "toolbelt:read-only@2"]
    assert body["config"] == {"preloadTools": ["web_search@v1"]}
    assert not session.selected_tools


def test_session_approve_posts_to_gateway():
    parent = make_parent(
        [
            FakeResponse(200, session_create_response()),
            FakeResponse(200, {"status": "approved"}),
        ]
    )
    session = SessionsOperations(parent, gateway_endpoint=TEST_GATEWAY_URL).create(
        "user-123"
    )

    result = session.approve("approval-123")

    request = parent._client._pipeline.calls[1].request
    assert request.url == f"{TEST_GATEWAY_URL}/approvals/approval-123"
    assert request.headers[SESSION_ID_HEADER] == "test-session"
    assert request.headers[ACTOR_ID_HEADER] == "user-123"
    assert json.loads(request.content) == {"decision": "approve"}
    assert result.status == "approved"


def test_session_deny_posts_to_gateway():
    parent = make_parent(
        [
            FakeResponse(200, session_create_response()),
            FakeResponse(200, {"status": "denied"}),
        ]
    )
    session = SessionsOperations(parent, gateway_endpoint=TEST_GATEWAY_URL).create(
        "user-123"
    )

    result = session.deny("approval-123")

    request = parent._client._pipeline.calls[1].request
    assert json.loads(request.content) == {"decision": "deny"}
    assert result.status == "denied"


def test_handle_tool_calls_preserves_approval_metadata():
    parent = make_parent(
        [
            FakeResponse(200, session_create_response()),
            FakeResponse(
                200,
                jsonrpc_result(
                    call_result(
                        structured={
                            "results": [
                                {
                                    "tool": "exa_web_search",
                                    "result": {
                                        "status": "failed",
                                        "error": {"message": "approval required"},
                                        "_meta": {
                                            "status": "requires_approval",
                                            "approval_id": "approval-123",
                                        },
                                    },
                                }
                            ]
                        },
                    )
                ),
            ),
        ]
    )
    session = SessionsOperations(parent, gateway_endpoint=TEST_GATEWAY_URL).create(
        "user-123"
    )

    messages = session.handle_tool_calls(chat_tool_response(name="exa_web_search"))
    content = json.loads(messages[0]["content"])
    assert content["_meta"]["approval_id"] == "approval-123"
