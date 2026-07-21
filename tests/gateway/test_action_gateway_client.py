# pylint: disable=missing-function-docstring,protected-access,missing-class-docstring,too-few-public-methods,import-outside-toplevel
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Smoke tests for ``from pydo.action_gateway import Client``."""

from __future__ import annotations

import json

import pytest

import pydo
import pydo.action_gateway
import pydo.aio
from pydo.action_gateway import Client as ActionGatewayClient
from pydo.gateway import ChatCompletionsProvider, MessagesProvider

from .conftest import (
    FakeResponse,
    chat_tool_response,
    invoke_envelope,
    session_create_response,
)

try:
    import aiohttp  # pylint: disable=unused-import

    _HAS_AIO = True
except ImportError:  # pragma: no cover
    _HAS_AIO = False


def test_namespace_module_exports():
    assert hasattr(pydo.action_gateway, "Client")
    assert hasattr(pydo.action_gateway, "Session")
    assert hasattr(pydo.action_gateway, "TokenCredentials")
    assert "Client" in pydo.action_gateway.__all__


def test_namespace_client_is_subclass_of_core_client():
    assert issubclass(ActionGatewayClient, pydo.Client)


def test_namespace_client_dir_is_gateway_focused():
    client = ActionGatewayClient(token="dummy")
    surface = set(dir(client))
    expected = {
        "sessions",
        "provider",
        "base_url",
        "chat",
        "messages",
        "responses",
    }
    assert expected <= surface
    for attr in ("tools", "code", "handle_tool_calls", "droplets"):
        assert attr not in surface


def test_namespace_client_repr_is_distinct():
    client = ActionGatewayClient(token="dummy")
    assert repr(client) == "<pydo.action_gateway.Client>"


def test_sessions_delegate_to_gateway():
    client = ActionGatewayClient(token="dummy")
    assert client.sessions is client.gateway.sessions
    assert client.provider is client.gateway.provider


def test_gateway_provider_kwarg():
    client = ActionGatewayClient(
        token="dummy",
        gateway_provider=MessagesProvider(),
    )
    assert isinstance(client.provider, MessagesProvider)
    assert not isinstance(client.provider, ChatCompletionsProvider)


def test_session_create_and_handle_tool_calls(monkeypatch):
    responses = [
        FakeResponse(200, session_create_response()),
        FakeResponse(200, invoke_envelope(output={"ok": True})),
    ]
    client = ActionGatewayClient(token="dummy")

    class Pipeline:
        def __init__(self):
            self.calls = []

        def run(self, request, **_kwargs):
            self.calls.append(request)
            return type("R", (), {"http_response": responses.pop(0)})()

    monkeypatch.setattr(client._client, "_pipeline", Pipeline())

    session = client.sessions.create(end_user_id="user-123")
    tools = session.tools()
    assert tools[0]["function"]["name"] == "action_search"
    assert "mcp/session/" in session.url

    messages = session.handle_tool_calls(chat_tool_response())
    assert messages[0]["role"] == "tool"
    create_body = json.loads(
        client._client._pipeline.calls[0].content
        if isinstance(client._client._pipeline.calls[0].content, str)
        else client._client._pipeline.calls[0].content.decode("utf-8")
    )
    assert create_body["end_user_id"] == "user-123"


@pytest.mark.skipif(not _HAS_AIO, reason="aiohttp extra not installed")
def test_async_namespace_mirrors_sync():
    import pydo.action_gateway.aio as action_gateway_aio
    from pydo.action_gateway.aio import Client as AsyncActionGatewayClient

    assert hasattr(action_gateway_aio, "Client")
    assert issubclass(action_gateway_aio.Client, pydo.aio.Client)
    client = AsyncActionGatewayClient(token="dummy")
    assert repr(client) == "<pydo.action_gateway.aio.Client>"
    assert client.sessions is client.gateway.sessions
