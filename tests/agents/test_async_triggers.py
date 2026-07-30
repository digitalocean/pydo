# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :mod:`pydo.aio.agents.custom_triggers`."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from pydo.aio.agents import AsyncAgentsResources
from pydo.agents import TriggerKind, TriggerStatus


class _FakeAsyncResponse:
    def __init__(self, status_code: int, body: Any = None):
        self.status_code = status_code
        if isinstance(body, (dict, list)):
            self._body_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            self._body_bytes = body.encode("utf-8")
        elif isinstance(body, bytes):
            self._body_bytes = body
        else:
            self._body_bytes = b""

    async def read(self) -> bytes:
        return self._body_bytes

    def text(self) -> str:
        return self._body_bytes.decode("utf-8")

    def body(self) -> bytes:
        return self._body_bytes


class _FakeAsyncPipeline:
    def __init__(self, responses: List[_FakeAsyncResponse]):
        self._responses = list(responses)
        self.calls: List[Any] = []

    async def run(self, request, *, stream=False):
        self.calls.append(SimpleNamespace(request=request, stream=stream))
        return SimpleNamespace(http_response=self._responses.pop(0))


def _make_async_resources(responses: List[_FakeAsyncResponse]) -> AsyncAgentsResources:
    parent = MagicMock()
    parent._client = MagicMock()
    parent._client._pipeline = _FakeAsyncPipeline(responses)
    return AsyncAgentsResources(
        parent, agents_endpoint="https://api.stage2.digitalocean.com"
    )


@pytest.mark.asyncio
async def test_async_list_and_create_triggers():
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(
                200, {"triggers": [{"trigger_id": "t1"}], "next_page_token": ""}
            ),
            _FakeAsyncResponse(
                201,
                {
                    "trigger": {"trigger_id": "t2", "kind": TriggerKind.CRON},
                },
            ),
        ]
    )

    listed = await resources.triggers.list(kind=TriggerKind.CRON)
    assert listed.triggers[0].trigger_id == "t1"
    list_call = resources._proxy._original._pipeline.calls[0]
    assert list_call.request.method == "GET"
    assert list_call.request.url.split("?", 1)[0].endswith("/v2/agents/triggers")
    assert "kind=cron" in list_call.request.url

    created = await resources.triggers.create(
        {
            "kind": TriggerKind.CRON,
            "name": "nightly",
            "session_mode": "fresh",
            "prompt_template": "run nightly",
            "output": {"mode": "none"},
            "session_template": "kind: Agent\n",
            "cron": {"cron_expr": "0 2 * * *", "timezone": "UTC"},
        }
    )
    assert created.trigger.trigger_id == "t2"
    create_call = resources._proxy._original._pipeline.calls[1]
    assert create_call.request.method == "POST"
    assert create_call.request.headers.get("Content-Type") == "application/json"


@pytest.mark.asyncio
async def test_async_update_delete_rotate_and_executions():
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(
                200, {"trigger": {"trigger_id": "t1", "status": TriggerStatus.PAUSED}}
            ),
            _FakeAsyncResponse(204),
            _FakeAsyncResponse(200, {"webhook_secret": "new"}),
            _FakeAsyncResponse(
                200, {"executions": [{"execution_id": "e1"}], "next_page_token": ""}
            ),
            _FakeAsyncResponse(
                200, {"execution": {"execution_id": "e1", "payload": "{}"}},
            ),
            _FakeAsyncResponse(200, {"trigger": {"trigger_id": "t1"}}),
            _FakeAsyncResponse(200, {"sessions": []}),
            _FakeAsyncResponse(200, {"providers": []}),
        ]
    )

    updated = await resources.triggers.update("t1", {"status": TriggerStatus.PAUSED})
    assert updated.trigger.status == "paused"
    assert resources._proxy._original._pipeline.calls[0].request.method == "PATCH"

    await resources.triggers.delete("t1")
    assert resources._proxy._original._pipeline.calls[1].request.method == "DELETE"

    rotated = await resources.triggers.rotate_secret("t1")
    assert rotated.webhook_secret == "new"

    executions = await resources.triggers.list_executions("t1")
    assert executions.executions[0].execution_id == "e1"

    execution = await resources.triggers.get_execution("t1", "e1")
    assert execution.execution.payload == "{}"

    by_session = await resources.triggers.get_by_session("s1")
    assert by_session.trigger.trigger_id == "t1"
    assert resources._proxy._original._pipeline.calls[5].request.url.endswith(
        "/v2/agents/triggers/by-session/s1"
    )

    await resources.triggers.list_reusable_sessions()
    assert resources._proxy._original._pipeline.calls[6].request.url.endswith(
        "/v2/agents/triggers/reusable-sessions"
    )

    await resources.triggers.list_webhook_providers()
    assert resources._proxy._original._pipeline.calls[7].request.url.endswith(
        "/v2/agents/webhook-providers"
    )
