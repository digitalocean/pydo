# pylint: disable=missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for Action Gateway sessions."""

from __future__ import annotations

import json

import pytest

from pydo.gateway import (
    SESSION_ID_HEADER,
    SessionsOperations,
    normalize_permissions,
)
from pydo.gateway.session import serialize_policy_json

from .conftest import (
    TEST_GATEWAY_URL,
    TEST_SESSION_URN,
    FakeResponse,
    chat_tool_response,
    invoke_envelope,
    make_parent,
    session_create_response,
)


def test_normalize_permissions_defaults_to_allow():
    assert normalize_permissions(None) == {"defaultAction": "allow", "rules": []}


def test_normalize_permissions_accepts_snake_case():
    policy = normalize_permissions(
        {
            "default_action": "ask",
            "rules": [
                {"toolbelt": "read-only@1.2.3", "action": "allow"},
                {"tool": "gmail", "action": "deny"},
            ],
        }
    )
    assert policy == {
        "defaultAction": "ask",
        "rules": [
            {"toolbelt": "read-only@1.2.3", "action": "allow"},
            {"tool": "gmail", "action": "deny"},
        ],
    }


def test_normalize_permissions_requires_tool_or_toolbelt():
    with pytest.raises(ValueError, match="tool or toolbelt"):
        normalize_permissions({"rules": [{"action": "allow"}]})


def test_serialize_policy_json():
    assert json.loads(serialize_policy_json(None))["defaultAction"] == "allow"


def test_sessions_create_requires_end_user_id():
    ops = SessionsOperations(make_parent([]), gateway_endpoint=TEST_GATEWAY_URL)
    with pytest.raises(ValueError, match="end_user_id"):
        ops.create("")


def test_sessions_create_posts_to_do_api_and_binds_rest():
    parent = make_parent(
        [
            FakeResponse(200, session_create_response()),
            FakeResponse(200, invoke_envelope(output={"ok": True})),
        ]
    )
    ops = SessionsOperations(parent, gateway_endpoint=TEST_GATEWAY_URL)
    session = ops.create("user-123")

    create_req = parent._client._pipeline.calls[0].request
    assert create_req.method == "POST"
    assert create_req.url.endswith("/v2/sessions")
    body = json.loads(create_req.content)
    assert body["end_user_id"] == "user-123"
    assert json.loads(body["policy_json"]) == {
        "defaultAction": "allow",
        "rules": [],
    }
    assert body["name"].startswith("pydo-session-")

    assert session.session_urn == TEST_SESSION_URN
    assert session.end_user_id == "user-123"
    assert session.url == "https://actions.do-ai-test.run/mcp/session/test-session"

    tools = session.tools()
    assert [t["function"]["name"] for t in tools][:1] == ["action_search"]

    messages = session.handle_tool_calls(chat_tool_response())
    invoke_req = parent._client._pipeline.calls[1].request
    assert invoke_req.url.endswith("/tools/invoke")
    assert invoke_req.headers[SESSION_ID_HEADER] == TEST_SESSION_URN
    assert messages[0]["role"] == "tool"


def test_sessions_create_with_permissions_and_name():
    parent = make_parent(
        [
            FakeResponse(
                200,
                session_create_response(name="named", end_user_id="u1"),
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
    assert json.loads(body["policy_json"]) == {
        "defaultAction": "deny",
        "rules": [{"tool": "web_search", "action": "allow"}],
    }
    assert session.name == "named"
