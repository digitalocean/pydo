# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :mod:`pydo.agents.custom_triggers`."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

from pydo.agents import (
    AgentsResources,
    TriggerKind,
    TriggerOutputMode,
    TriggerSessionMode,
    TriggerStatus,
    WebhookProviderKey,
)

# ---------------------------------------------------------------------------
# Fake pipeline / response plumbing (mirrors test_sessions.py)
# ---------------------------------------------------------------------------


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

    def run(self, request, *, stream=False):
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


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_list_triggers_with_filters():
    body = {
        "triggers": [{"trigger_id": "t1", "kind": TriggerKind.WEBHOOK}],
        "next_page_token": "next",
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.triggers.list(
        page_size=10,
        page_token="tok",
        kind=TriggerKind.WEBHOOK,
        status=TriggerStatus.ACTIVE,
    )

    call = _last_call(resources)
    assert call.request.method == "GET"
    assert _path(call.request.url).endswith("/v2/agents/triggers")
    assert "page_size=10" in call.request.url
    assert "page_token=tok" in call.request.url
    assert "kind=webhook" in call.request.url
    assert "status=active" in call.request.url
    assert resp.triggers[0].trigger_id == "t1"
    assert resp.next_page_token == "next"


def test_create_webhook_trigger_returns_secret_once():
    body = {
        "trigger": {
            "trigger_id": "t-new",
            "kind": TriggerKind.WEBHOOK,
            "name": "gh-prs",
            "status": TriggerStatus.ACTIVE,
            "session_mode": TriggerSessionMode.FRESH,
            "webhook": {
                "provider": WebhookProviderKey.GITHUB,
                "webhook_url": "https://api.digitalocean.com/v2/agents/triggers/t-new/webhook",
            },
        },
        "webhook_secret": "whsec_shown_once",
    }
    resources = _make_resources([_FakeResponse(201, body)])

    create_body = {
        "kind": TriggerKind.WEBHOOK,
        "name": "gh-prs",
        "session_mode": TriggerSessionMode.FRESH,
        "prompt_template": "Review PR {{payload.pull_request.number}}",
        "output": {"mode": TriggerOutputMode.NONE},
        "session_template": "kind: Agent\n",
        "webhook": {"provider": WebhookProviderKey.GITHUB},
    }
    resp = resources.triggers.create(create_body)

    call = _last_call(resources)
    assert call.request.method == "POST"
    assert call.request.url.endswith("/v2/agents/triggers")
    assert call.request.headers.get("Content-Type") == "application/json"
    assert json.loads(call.request.content) == create_body
    assert resp.trigger.trigger_id == "t-new"
    assert resp.webhook_secret == "whsec_shown_once"


def test_create_rejects_empty_body():
    resources = _make_resources([])
    with pytest.raises(ValueError, match="non-empty"):
        resources.triggers.create({})


def test_get_trigger():
    body = {"trigger": {"trigger_id": "t1", "name": "nightly"}}
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.triggers.get("t1")

    call = _last_call(resources)
    assert call.request.method == "GET"
    assert call.request.url.endswith("/v2/agents/triggers/t1")
    assert resp.trigger.name == "nightly"


def test_update_pause_trigger():
    body = {
        "trigger": {
            "trigger_id": "t1",
            "status": TriggerStatus.PAUSED,
        }
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.triggers.update("t1", {"status": TriggerStatus.PAUSED})

    call = _last_call(resources)
    assert call.request.method == "PATCH"
    assert call.request.url.endswith("/v2/agents/triggers/t1")
    assert json.loads(call.request.content) == {"status": "paused"}
    assert resp.trigger.status == "paused"


def test_delete_trigger_returns_none_on_204():
    resources = _make_resources([_FakeResponse(204)])

    assert resources.triggers.delete("t1") is None

    call = _last_call(resources)
    assert call.request.method == "DELETE"
    assert call.request.url.endswith("/v2/agents/triggers/t1")


def test_rotate_secret():
    body = {"webhook_secret": "whsec_rotated"}
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.triggers.rotate_secret("t1")

    call = _last_call(resources)
    assert call.request.method == "POST"
    assert call.request.url.endswith("/v2/agents/triggers/t1/rotate-secret")
    assert resp.webhook_secret == "whsec_rotated"


# ---------------------------------------------------------------------------
# Executions & lookups
# ---------------------------------------------------------------------------


def test_list_executions():
    body = {
        "executions": [{"execution_id": "e1", "status": "succeeded"}],
        "next_page_token": "",
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.triggers.list_executions(
        "t1", page_size=5, status="succeeded"
    )

    call = _last_call(resources)
    assert call.request.method == "GET"
    assert _path(call.request.url).endswith("/v2/agents/triggers/t1/executions")
    assert "page_size=5" in call.request.url
    assert "status=succeeded" in call.request.url
    assert resp.executions[0].execution_id == "e1"


def test_get_execution_includes_payload():
    body = {
        "execution": {
            "execution_id": "e1",
            "payload": '{"action":"opened"}',
            "output_text": "done",
            "output_truncated": False,
        }
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.triggers.get_execution("t1", "e1")

    call = _last_call(resources)
    assert call.request.url.endswith("/v2/agents/triggers/t1/executions/e1")
    assert resp.execution.payload == '{"action":"opened"}'
    assert resp.execution.output_text == "done"


def test_get_by_session():
    body = {"trigger": {"trigger_id": "t1", "bound_session_id": "s1"}}
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.triggers.get_by_session("s1")

    call = _last_call(resources)
    assert call.request.url.endswith("/v2/agents/triggers/by-session/s1")
    assert resp.trigger.trigger_id == "t1"


def test_list_reusable_sessions():
    body = {
        "sessions": [
            {
                "session_id": "s1",
                "status": "SESSION_STATUS_PAUSED",
            }
        ]
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.triggers.list_reusable_sessions(page_size=20)

    call = _last_call(resources)
    assert _path(call.request.url).endswith("/v2/agents/triggers/reusable-sessions")
    assert "page_size=20" in call.request.url
    assert resp.sessions[0].session_id == "s1"


def test_list_webhook_providers():
    body = {
        "providers": [
            {
                "key": "github",
                "display_name": "GitHub",
                "signature": {
                    "header": "X-Hub-Signature-256",
                    "scheme": "hmac-sha256",
                },
            }
        ]
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.triggers.list_webhook_providers()

    call = _last_call(resources)
    assert call.request.method == "GET"
    assert call.request.url.endswith("/v2/agents/webhook-providers")
    assert resp.providers[0].key == "github"


def test_path_segments_are_url_encoded():
    resources = _make_resources(
        [_FakeResponse(200, {"trigger": {"trigger_id": "a/b"}})]
    )
    resources.triggers.get("a/b")

    call = _last_call(resources)
    assert call.request.url.endswith("/v2/agents/triggers/a%2Fb")


def test_404_maps_to_resource_not_found():
    resources = _make_resources([_FakeResponse(404, {"error": {"message": "gone"}})])
    with pytest.raises(ResourceNotFoundError):
        resources.triggers.get("missing")


def test_500_raises_http_response_error():
    resources = _make_resources(
        [_FakeResponse(500, {"error": {"message": "boom"}})]
    )
    with pytest.raises(HttpResponseError):
        resources.triggers.list()
