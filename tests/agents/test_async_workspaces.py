# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :mod:`pydo.aio.agents.custom_workspaces`."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import (
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
)

from pydo.aio.agents import AsyncAgentsResources

_WORKSPACE = {
    "workspace_id": "ws-1",
    "state": "AVAILABLE",
    "size_gibibytes": 10,
    "bytes_used": 0,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


class _FakeAsyncResponse:
    def __init__(self, status_code: int, body: Any = None):
        self.status_code = status_code
        self.reason = None
        if isinstance(body, (dict, list)):
            self._body_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            self._body_bytes = body.encode("utf-8")
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
    return AsyncAgentsResources(parent, agents_endpoint="https://api.digitalocean.com")


def _last_call(resources: AsyncAgentsResources):
    return resources._proxy._original._pipeline.calls[-1]


def _error(code: int, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


@pytest.mark.asyncio
async def test_async_create_workspace_and_idempotency_key():
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(201, {"workspace": _WORKSPACE}),
            _FakeAsyncResponse(200, {"workspace": _WORKSPACE}),
        ]
    )

    created = await resources.workspaces.create(10, name="scratch")
    call = _last_call(resources)
    assert call.request.method == "POST"
    assert call.request.url.endswith("/v2/agents/workspaces")
    assert json.loads(call.request.content) == {
        "size_gibibytes": 10,
        "name": "scratch",
    }
    assert "Idempotency-Key" not in call.request.headers
    assert created.workspace.workspace_id == "ws-1"

    replay = await resources.workspaces.create(
        10, name="scratch", idempotency_key="key-123"
    )
    assert _last_call(resources).request.headers.get("Idempotency-Key") == "key-123"
    assert replay.workspace.workspace_id == "ws-1"


@pytest.mark.asyncio
async def test_async_create_workspace_rejects_invalid_size():
    resources = _make_async_resources([])
    with pytest.raises(ValueError, match="size_gibibytes"):
        await resources.workspaces.create(0)


@pytest.mark.asyncio
async def test_async_list_get_delete_workspace():
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(
                200, {"workspaces": [_WORKSPACE], "next_page_token": "next"}
            ),
            _FakeAsyncResponse(200, {"workspace": _WORKSPACE}),
            _FakeAsyncResponse(204),
        ]
    )

    listed = await resources.workspaces.list(page_size=25, page_token="tok")
    list_call = resources._proxy._original._pipeline.calls[0]
    assert list_call.request.method == "GET"
    assert "page_size=25" in list_call.request.url
    assert "page_token=tok" in list_call.request.url
    assert listed.next_page_token == "next"

    got = await resources.workspaces.get("ws-1")
    get_call = resources._proxy._original._pipeline.calls[1]
    assert get_call.request.url.endswith("/v2/agents/workspaces/ws-1")
    assert got.workspace.size_gibibytes == 10

    assert await resources.workspaces.delete("ws-1") is None
    delete_call = resources._proxy._original._pipeline.calls[2]
    assert delete_call.request.method == "DELETE"
    assert delete_call.request.url.endswith("/v2/agents/workspaces/ws-1")


@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore:coroutine .* was never awaited:RuntimeWarning")
async def test_async_workspace_errors():
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(404, _error(404, "not found")),
            _FakeAsyncResponse(409, _error(409, "not AVAILABLE or FAILED")),
            _FakeAsyncResponse(422, _error(422, "idempotency key reused")),
            _FakeAsyncResponse(501, _error(501, "workspaces are not enabled")),
        ]
    )

    with pytest.raises(ResourceNotFoundError):
        await resources.workspaces.get("missing")
    with pytest.raises(ResourceExistsError):
        await resources.workspaces.delete("ws-1")
    with pytest.raises(HttpResponseError) as excinfo:
        await resources.workspaces.create(10, idempotency_key="k")
    assert excinfo.value.status_code == 422
    with pytest.raises(HttpResponseError) as excinfo:
        await resources.workspaces.create(10)
    assert excinfo.value.status_code == 501
    assert "workspaces are not enabled" in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_create_session_from_config_sends_workspace_id_in_body():
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(
                200, {"session": {"session_id": "s-1", "workspace_id": "ws-1"}}
            ),
            _FakeAsyncResponse(200, {"session": {"session_id": "s-2"}}),
        ]
    )

    resp = await resources.sessions.create_from_config(
        name="run-1", config_id="cfg-1", workspace_id="ws-1"
    )
    assert json.loads(_last_call(resources).request.content) == {
        "name": "run-1",
        "config_id": "cfg-1",
        "workspace_id": "ws-1",
    }
    assert resp.session.workspace_id == "ws-1"

    await resources.sessions.create_from_config(name="run-2", config_id="cfg-1")
    assert "workspace_id" not in json.loads(_last_call(resources).request.content)


@pytest.mark.asyncio
async def test_async_create_session_from_manifest_sends_workspace_id_as_query():
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(200, {"session": {"session_id": "s-1"}}),
            _FakeAsyncResponse(200, {"session": {"session_id": "s-2"}}),
        ]
    )

    await resources.sessions.create_from_manifest("kind: Agent\n", workspace_id="ws-1")
    call = _last_call(resources)
    assert call.request.headers.get("Content-Type") == "application/x-yaml"
    assert "workspace_id=ws-1" in call.request.url

    await resources.start("kind: Agent\n", workspace_id="ws-2")
    assert "workspace_id=ws-2" in _last_call(resources).request.url
