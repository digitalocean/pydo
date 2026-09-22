# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :mod:`pydo.aio.agents.custom_configs`."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from pydo.aio.agents import AsyncAgentsResources
from pydo.agents import SessionStatus


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

    async def run(self, request, *, stream=False, **kwargs):
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
async def test_async_configs_crud_and_sessions():
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(
                200,
                {"configs": [{"id": "cfg-1", "name": "demo"}], "next_page_token": ""},
            ),
            _FakeAsyncResponse(
                201,
                {"config": {"id": "cfg-2", "name": "new"}},
            ),
            _FakeAsyncResponse(204),
            _FakeAsyncResponse(
                200,
                {"sessions": [{"session_id": "sess-1"}]},
            ),
        ]
    )

    listed = await resources.configs.list(page_size=50)
    assert listed.configs[0].id == "cfg-1"
    list_call = resources._proxy._original._pipeline.calls[0]
    assert list_call.request.method == "GET"
    assert list_call.request.url.split("?", 1)[0].endswith("/v2/agents/configs")

    created = await resources.configs.create(
        {"name": "new", "manifest_yaml": "kind: Agent\n"}
    )
    assert created.config.id == "cfg-2"

    await resources.configs.delete("cfg-2")
    delete_call = resources._proxy._original._pipeline.calls[2]
    assert delete_call.request.method == "DELETE"

    sessions = await resources.configs.list_sessions(
        "cfg-1",
        status=SessionStatus.READY,
    )
    assert sessions.sessions[0].session_id == "sess-1"
    sessions_call = resources._proxy._original._pipeline.calls[3]
    assert "status=SESSION_STATUS_READY" in sessions_call.request.url


@pytest.mark.asyncio
async def test_async_create_session_from_config():
    resources = _make_async_resources(
        [_FakeAsyncResponse(200, {"session": {"session_id": "sess-x"}})]
    )

    resp = await resources.sessions.create_from_config(
        name="run",
        config_id="cfg-1",
    )
    assert resp.session.session_id == "sess-x"
    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "POST"
    assert call.request.headers.get("Content-Type") == "application/json"
