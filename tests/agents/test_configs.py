# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :mod:`pydo.agents.custom_configs`."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import HttpResponseError

from pydo.agents import AgentsResources, SessionStatus


class _FakeResponse:
    def __init__(self, status_code: int, body: Any = None):
        self.status_code = status_code
        self.reason = None
        if isinstance(body, (dict, list)):
            self._body_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            self._body_bytes = body.encode("utf-8")
        elif isinstance(body, bytes):
            self._body_bytes = body
        else:
            self._body_bytes = b""

    def text(self) -> str:
        return self._body_bytes.decode("utf-8")

    def body(self) -> bytes:
        return self._body_bytes

    def read(self) -> bytes:
        return self._body_bytes

    def close(self) -> None:
        pass


def _path(url: str) -> str:
    return url.split("?", 1)[0]


class _FakePipeline:
    def __init__(self, responses: List[_FakeResponse]):
        self._responses = list(responses)
        self.calls: List[Any] = []

    def run(self, request, *, stream=False, **kwargs):
        self.calls.append(SimpleNamespace(request=request, stream=stream))
        response = self._responses.pop(0)
        return SimpleNamespace(http_response=response)


def _make_resources(responses: List[_FakeResponse]) -> AgentsResources:
    parent = MagicMock()
    parent._client = MagicMock()
    parent._client._pipeline = _FakePipeline(responses)
    return AgentsResources(
        parent, agents_endpoint="https://api.stage2.digitalocean.com"
    )


def _last_call(resources: AgentsResources):
    return resources._proxy._original._pipeline.calls[-1]


def test_list_configs_pagination():
    body = {
        "configs": [{"id": "cfg-1", "name": "my-agent"}],
        "next_page_token": "next",
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.configs.list(page_size=25, page_token="tok")

    call = _last_call(resources)
    assert call.request.method == "GET"
    assert _path(call.request.url).endswith("/v2/agents/configs")
    assert "page_size=25" in call.request.url
    assert "page_token=tok" in call.request.url
    assert resp.configs[0].id == "cfg-1"
    assert resp.next_page_token == "next"


def test_create_config():
    manifest = "kind: Agent\nmetadata:\n  name: demo\n"
    body = {
        "config": {
            "id": "cfg-new",
            "name": "demo",
            "manifest": {"kind": "Agent"},
        }
    }
    resources = _make_resources([_FakeResponse(201, body)])

    resp = resources.configs.create({"name": "demo", "manifest_yaml": manifest})

    call = _last_call(resources)
    assert call.request.method == "POST"
    assert _path(call.request.url).endswith("/v2/agents/configs")
    assert call.request.headers.get("Content-Type") == "application/json"
    assert resp.config.id == "cfg-new"


def test_create_config_rejects_empty_body():
    resources = _make_resources([])
    with pytest.raises(ValueError, match="non-empty dict"):
        resources.configs.create({})


def test_get_config():
    body = {"config": {"id": "cfg-1", "name": "demo"}}
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.configs.get("cfg-1")

    call = _last_call(resources)
    assert call.request.method == "GET"
    assert _path(call.request.url).endswith("/v2/agents/configs/cfg-1")
    assert resp.config.name == "demo"


def test_delete_config():
    resources = _make_resources([_FakeResponse(204)])

    resources.configs.delete("cfg-1")

    call = _last_call(resources)
    assert call.request.method == "DELETE"
    assert _path(call.request.url).endswith("/v2/agents/configs/cfg-1")


def test_list_config_sessions_with_status_filter():
    body = {"sessions": [{"session_id": "sess-1", "config_id": "cfg-1"}]}
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.configs.list_sessions(
        "cfg-1",
        page_size=10,
        page_token="tok",
        status=SessionStatus.ALL,
    )

    call = _last_call(resources)
    assert call.request.method == "GET"
    assert _path(call.request.url).endswith("/v2/agents/configs/cfg-1/sessions")
    assert "status=SESSION_STATUS_ALL" in call.request.url
    assert resp.sessions[0].session_id == "sess-1"


def test_create_session_from_config():
    body = {"session": {"session_id": "sess-new", "config_id": "cfg-1"}}
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.sessions.create_from_config(
        name="run-1",
        config_id="cfg-1",
    )

    call = _last_call(resources)
    assert call.request.method == "POST"
    assert _path(call.request.url).endswith("/v2/agents/sessions")
    assert call.request.headers.get("Content-Type") == "application/json"
    assert resp.session.session_id == "sess-new"


def test_delete_config_active_sessions_raises():
    resources = _make_resources(
        [
            _FakeResponse(
                409,
                {"id": "conflict", "message": "active sessions remain"},
            )
        ]
    )

    with pytest.raises(HttpResponseError):
        resources.configs.delete("cfg-1")
