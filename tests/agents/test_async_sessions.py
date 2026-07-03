# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :mod:`pydo.aio.agents.custom_sessions`."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from pydo.aio.agents import AsyncAgentsResources


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
async def test_async_create_from_manifest_uploads_yaml_verbatim():
    resources = _make_async_resources(
        [_FakeAsyncResponse(200, {"session": {"session_id": "abc"}})]
    )
    manifest = "apiVersion: agents.digitalocean.com/v1alpha1\nkind: Agent\n"

    resp = await resources.sessions.create_from_manifest(manifest)

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "POST"
    assert call.request.url.endswith("/v2/agents/sessions")
    assert call.request.headers.get("Content-Type") == "application/x-yaml"
    content = call.request.content
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    assert content == manifest
    assert resp.session.session_id == "abc"


@pytest.mark.asyncio
async def test_async_create_from_manifest_rejects_empty():
    resources = _make_async_resources([])
    with pytest.raises(ValueError):
        await resources.sessions.create_from_manifest("")


@pytest.mark.asyncio
async def test_async_list_filters_by_name():
    resources = _make_async_resources([_FakeAsyncResponse(200, {"sessions": []})])
    await resources.sessions.list(name="my-session")

    call = resources._proxy._original._pipeline.calls[0]
    assert "name=my-session" in call.request.url


@pytest.mark.asyncio
async def test_async_attach_by_name_picks_most_recent_match():
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(
                200,
                {
                    "sessions": [
                        {
                            "session_id": "old",
                            "name": "dup",
                            "created_at": "2026-01-01T00:00:00Z",
                        },
                        {
                            "session_id": "new",
                            "name": "dup",
                            "created_at": "2026-07-01T00:00:00Z",
                        },
                    ]
                },
            )
        ]
    )
    agent = await resources.attach_by_name("dup")
    assert agent.session_id == "new"


@pytest.mark.asyncio
async def test_async_attach_by_name_raises_when_not_found():
    resources = _make_async_resources([_FakeAsyncResponse(200, {"sessions": []})])
    with pytest.raises(LookupError):
        await resources.attach_by_name("missing")
