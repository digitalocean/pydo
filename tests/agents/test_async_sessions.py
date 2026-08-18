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
    def __init__(self, status_code: int, body: Any = None, *, sse_chunks=None):
        self.status_code = status_code
        if isinstance(body, (dict, list)):
            self._body_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            self._body_bytes = body.encode("utf-8")
        elif isinstance(body, bytes):
            self._body_bytes = body
        else:
            self._body_bytes = b""
        self._sse = sse_chunks

    async def read(self) -> bytes:
        return self._body_bytes

    def text(self) -> str:
        return self._body_bytes.decode("utf-8")

    def body(self) -> bytes:
        return self._body_bytes

    async def iter_bytes(self):
        for chunk in self._sse or []:
            yield chunk

    def close(self) -> None:
        pass


class _FakeAsyncPipeline:
    def __init__(self, responses: List[_FakeAsyncResponse]):
        self._responses = list(responses)
        self.calls: List[Any] = []

    async def run(self, request, *, stream=False, **kwargs):
        self.calls.append(
            SimpleNamespace(request=request, stream=stream, kwargs=kwargs)
        )
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
async def test_async_pause_session():
    resources = _make_async_resources(
        [_FakeAsyncResponse(200, {"session": {"session_id": "abc-123"}})]
    )
    await resources.sessions.pause("abc-123")

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "POST"
    assert call.request.url.endswith("/v2/agents/sessions/abc-123/pause")


@pytest.mark.asyncio
async def test_async_resume_session():
    resources = _make_async_resources(
        [_FakeAsyncResponse(200, {"session": {"session_id": "abc-123"}})]
    )
    await resources.sessions.resume("abc-123")

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "POST"
    assert call.request.url.endswith("/v2/agents/sessions/abc-123/resume")


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


# ---------------------------------------------------------------------------
# Backward history paging
# ---------------------------------------------------------------------------

_HISTORY_PAGE_SSE = (
    b": connected to s1\n\n"
    b'data: {"event_id":"e10","type":"run.token_delta","data":{"text":"older "}}\n\n'
    b'data: {"event_id":"e11","type":"run.token_delta","data":{"text":"newer"}}\n\n'
    b": has_more=true\n\n"
)


async def _drain(stream) -> list:
    return [event async for event in stream]


@pytest.mark.asyncio
async def test_async_stream_before_implies_replay_only_and_sends_limit():
    resources = _make_async_resources([_FakeAsyncResponse(200, sse_chunks=[b""])])

    await _drain(await resources.sessions.stream("s1", before="evt-99", limit=50))

    url = resources._proxy._original._pipeline.calls[0].request.url
    assert "before=evt-99" in url
    assert "limit=50" in url
    assert "replay_only=true" in url


@pytest.mark.asyncio
async def test_async_stream_omits_paging_params_when_unset():
    resources = _make_async_resources([_FakeAsyncResponse(200, sse_chunks=[b""])])

    await _drain(await resources.sessions.stream("s1"))

    url = resources._proxy._original._pipeline.calls[0].request.url
    assert "before=" not in url
    assert "limit=" not in url
    assert "replay_only=" not in url


@pytest.mark.asyncio
async def test_async_stream_rejects_limit_without_before():
    resources = _make_async_resources([])
    with pytest.raises(ValueError, match="before"):
        await resources.sessions.stream("s1", limit=10)


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, -1])
async def test_async_stream_rejects_non_positive_limit(limit):
    resources = _make_async_resources([])
    with pytest.raises(ValueError, match="positive"):
        await resources.sessions.stream("s1", before="evt-99", limit=limit)


@pytest.mark.asyncio
async def test_async_stream_records_has_more_comment():
    resources = _make_async_resources(
        [_FakeAsyncResponse(200, sse_chunks=[_HISTORY_PAGE_SSE])]
    )

    stream = await resources.sessions.stream("s1", before="evt-12")
    assert stream.has_more is None

    events = await _drain(stream)
    assert [e.event_id for e in events] == ["e10", "e11"]
    assert stream.has_more is True
    assert stream.oldest_event_id == "e10"


@pytest.mark.asyncio
async def test_async_stream_drops_tenant_id():
    sse_payload = (
        b'data: {"event_id":"e1","tenant_id":"10212320","session_id":"s1",'
        b'"seq":1,"type":"run.token_delta","data":{"text":"hello"}}\n\n'
    )
    resources = _make_async_resources(
        [_FakeAsyncResponse(200, sse_chunks=[sse_payload])]
    )

    events = await _drain(await resources.sessions.stream("s1"))
    assert "tenant_id" not in events[0]
    assert "team_id" not in events[0]
    assert events[0].event_id == "e1"
    assert events[0].data.text == "hello"


@pytest.mark.asyncio
async def test_async_history_page_returns_events_cursor_and_has_more():
    resources = _make_async_resources(
        [_FakeAsyncResponse(200, sse_chunks=[_HISTORY_PAGE_SSE])]
    )

    page = await resources.sessions.history_page("s1", before="evt-12", limit=2)

    url = resources._proxy._original._pipeline.calls[0].request.url
    assert "before=evt-12" in url
    assert "limit=2" in url
    assert "replay_only=true" in url

    events, has_more, next_before = page
    assert [e.event_id for e in events] == ["e10", "e11"]
    assert has_more is True
    assert next_before == "e10"


@pytest.mark.asyncio
async def test_async_history_page_empty_has_no_cursor():
    resources = _make_async_resources(
        [_FakeAsyncResponse(200, sse_chunks=[b": has_more=false\n\n"])]
    )

    page = await resources.sessions.history_page("s1", before="e1")
    assert page.events == []
    assert page.has_more is False
    assert page.next_before is None


@pytest.mark.asyncio
async def test_async_history_page_requires_before():
    resources = _make_async_resources([])
    with pytest.raises(ValueError, match="before"):
        await resources.sessions.history_page("s1", before="")


@pytest.mark.asyncio
async def test_async_agent_session_history_binds_session_id():
    resources = _make_async_resources(
        [_FakeAsyncResponse(200, sse_chunks=[_HISTORY_PAGE_SSE])]
    )

    page = await resources.attach("s1").history(before="evt-12")

    url = resources._proxy._original._pipeline.calls[0].request.url
    assert "/v2/agents/sessions/s1/stream" in url
    assert page.next_before == "e10"
