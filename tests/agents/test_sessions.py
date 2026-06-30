# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :mod:`pydo.agents.custom_sessions`."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from pydo.agents import (
    AgentsResources,
    HITLOutcome,
    HarnessStreamError,
    OAuthProvider,
    ResolutionSource,
    SessionStatus,
    resolve_agents_base_url,
)

# ---------------------------------------------------------------------------
# Fake pipeline / response plumbing
# ---------------------------------------------------------------------------


class _FakeResponse:
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

    def text(self) -> str:
        return self._body_bytes.decode("utf-8")

    def body(self) -> bytes:
        return self._body_bytes

    def read(self) -> bytes:
        return self._body_bytes

    def iter_bytes(self):
        for chunk in self._sse or []:
            yield chunk

    def close(self) -> None:
        pass


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


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


def test_create_from_manifest_uploads_yaml_verbatim():
    body = {"session": {"session_id": "abc", "status": SessionStatus.PROVISIONING}}
    resources = _make_resources([_FakeResponse(200, body)])

    manifest = (
        "apiVersion: agents.digitalocean.com/v1alpha1\n"
        "kind: Agent\n"
        "metadata:\n"
        "  name: harness-demo\n"
    )
    resp = resources.sessions.create_from_manifest(manifest)

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "POST"
    assert call.request.url.endswith("/v2/agents/sessions")
    assert call.request.headers.get("Content-Type") == "application/x-yaml"
    content = call.request.content
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    assert content == manifest
    assert resp.session.session_id == "abc"


def test_create_from_manifest_accepts_bytes():
    resources = _make_resources([_FakeResponse(200, {"session": {"session_id": "z"}})])
    resources.sessions.create_from_manifest(b"kind: Agent\n")

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.headers.get("Content-Type") == "application/x-yaml"


def test_create_from_manifest_rejects_empty():
    resources = _make_resources([])
    with pytest.raises(ValueError):
        resources.sessions.create_from_manifest("   \n  ")


def test_get_session_url_encodes_id():
    resources = _make_resources(
        [_FakeResponse(200, {"session": {"session_id": "x/y"}})]
    )
    resources.sessions.get("x/y")

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "GET"
    assert call.request.url.endswith("/v2/agents/sessions/x%2Fy")


def test_destroy_session():
    resources = _make_resources([_FakeResponse(200, "")])
    resources.sessions.destroy("abc-123")

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "DELETE"
    assert call.request.url.endswith("/v2/agents/sessions/abc-123")


def test_list_sessions_propagates_query_params():
    resources = _make_resources(
        [_FakeResponse(200, {"sessions": [], "next_page_token": ""})]
    )
    resources.sessions.list(page_token="tok", page_size=10, status=SessionStatus.READY)

    call = resources._proxy._original._pipeline.calls[0]
    raw = call.request.url
    assert "page_token=tok" in raw
    assert "page_size=10" in raw
    assert "status=SESSION_STATUS_READY" in raw


def test_send_input_body_shape():
    resources = _make_resources([_FakeResponse(200, {"run_id": "r1"})])
    resp = resources.sessions.send_input("s1", text="hello world")

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "POST"
    assert call.request.url.endswith("/v2/agents/sessions/s1/input")
    assert json.loads(call.request.content) == {"text": "hello world"}
    assert resp.run_id == "r1"


def test_resolve_hitl_url_and_body():
    resources = _make_resources([_FakeResponse(200, "")])
    resources.sessions.resolve_hitl(
        "s1",
        "req-9",
        outcome=HITLOutcome.APPROVE,
        reason="looks safe",
        source=ResolutionSource.OUT_OF_BAND,
    )

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.url.endswith("/v2/agents/sessions/s1/hitl/req-9")
    assert json.loads(call.request.content) == {
        "outcome": "HITL_OUTCOME_APPROVE",
        "reason": "looks safe",
        "source": "RESOLUTION_SOURCE_OUT_OF_BAND",
    }


def test_start_oauth_flow():
    body = {
        "authorize_url": "https://github.com/login/oauth/authorize?...",
        "flow_kind": "OAUTH_FLOW_KIND_WEB_CALLBACK",
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.sessions.start_oauth_flow(
        "s1",
        OAuthProvider.GITHUB,
        requested_scopes=["repo"],
    )

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.url.endswith(
        "/v2/agents/sessions/s1/oauth/OAUTH_PROVIDER_GITHUB"
    )
    assert json.loads(call.request.content) == {"requested_scopes": ["repo"]}
    assert resp.flow_kind == "OAUTH_FLOW_KIND_WEB_CALLBACK"


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


def test_stream_unwraps_spi_canonical_envelope():
    sse_payload = (
        b'data: {"event_id":"e1","type":"run.token_delta","data":{"text":"hello "}}\n\n'
        b'data: {"event_id":"e2","type":"run.token_delta","data":{"text":"world"}}\n\n'
        b'data: {"event_id":"e3","type":"run.completed","data":{"run_cost_micros":1234}}\n\n'
    )
    resources = _make_resources([_FakeResponse(200, sse_chunks=[sse_payload])])

    events = list(resources.sessions.stream("s1"))
    assert events[0].type == "run.token_delta"
    assert events[0].data.text == "hello "
    assert events[1].data.text == "world"
    assert events[2].type == "run.completed"
    assert events[2].data.run_cost_micros == 1234


def test_stream_unwraps_result_envelope():
    sse_payload = (
        b'data: {"result":{"event_id":"e1","token_chunk":{"text":"hello "}}}\n\n'
        b'data: {"result":{"event_id":"e2","token_chunk":{"text":"world"}}}\n\n'
        b'data: {"result":{"event_id":"e3","run_completed":{"run_cost_micros":1234}}}\n\n'
    )
    resources = _make_resources([_FakeResponse(200, sse_chunks=[sse_payload])])

    events = list(resources.sessions.stream("s1"))
    assert events[0].token_chunk.text == "hello "
    assert events[1].token_chunk.text == "world"
    assert events[2].run_completed.run_cost_micros == 1234


def test_stream_error_envelope_raises():
    sse_payload = (
        b'data: {"error":{"grpc_code":9,"http_code":412,"message":"not ready"}}\n\n'
    )
    resources = _make_resources([_FakeResponse(200, sse_chunks=[sse_payload])])

    with pytest.raises(HarnessStreamError) as excinfo:
        list(resources.sessions.stream("s1"))

    assert excinfo.value.grpc_code == 9
    assert excinfo.value.http_code == 412
    assert "not ready" in str(excinfo.value)


def test_stream_passes_replay_query_params():
    sse_payload = b""
    resources = _make_resources([_FakeResponse(200, sse_chunks=[sse_payload])])

    stream = resources.sessions.stream("s1", replay_from="evt-42", replay_only=True)
    list(stream)

    call = resources._proxy._original._pipeline.calls[0]
    assert "replay_from=evt-42" in call.request.url
    assert "replay_only=true" in call.request.url


def test_resolve_agents_base_url_adds_https_scheme():
    assert (
        resolve_agents_base_url("api.digitalocean.com")
        == "https://api.digitalocean.com"
    )
    assert resolve_agents_base_url("http://127.0.0.1:8080") == "http://127.0.0.1:8080"
