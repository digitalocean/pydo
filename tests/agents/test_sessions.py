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
from azure.core.exceptions import HttpResponseError

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
    def __init__(
        self, status_code: int, body: Any = None, *, sse_chunks=None, reason: str = ""
    ):
        self.status_code = status_code
        self.reason = reason
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

    def run(self, request, *, stream=False, **kwargs):
        self.calls.append(
            SimpleNamespace(request=request, stream=stream, kwargs=kwargs)
        )
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


def test_create_from_manifest_strips_team_id_and_tenant_id():
    body = {
        "session": {
            "session_id": "abc",
            "status": SessionStatus.PROVISIONING,
            "team_id": 10212320,
            "tenant_id": "10212320",
        }
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.sessions.create_from_manifest("kind: Agent\n")

    assert resp.session.session_id == "abc"
    assert "team_id" not in resp.session
    assert "tenant_id" not in resp.session


def test_create_from_manifest_preserves_multiline_skill_instructions():
    # spec.skills is forwarded raw, like the rest of the manifest — no client-side
    # parsing/re-marshaling happens, so a multi-line `instructions` block scalar
    # must survive byte-for-byte.
    body = {"session": {"session_id": "abc", "status": SessionStatus.PROVISIONING}}
    resources = _make_resources([_FakeResponse(200, body)])

    manifest = (
        "apiVersion: agents.digitalocean.com/v1alpha1\n"
        "kind: Agent\n"
        "metadata:\n"
        "  name: harness-demo\n"
        "spec:\n"
        "  skills:\n"
        "    - name: release-notes\n"
        "      description: Draft release notes from a diff.\n"
        "      instructions: |\n"
        "        Summarize the diff in Keep a Changelog format.\n"
        "        Group entries under Added/Changed/Fixed.\n"
    )
    resources.sessions.create_from_manifest(manifest)

    call = resources._proxy._original._pipeline.calls[0]
    content = call.request.content
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    assert content == manifest


def test_create_from_manifest_surfaces_skills_size_cap_error():
    # harness-api rejects an oversized spec.skills list with a nested
    # {"error": {"code", "message"}} envelope. azure-core's OData-v4 error
    # parsing already extracts a clean message from this shape — no SDK
    # code change needed, this just proves it.
    message = (
        "agentspec: spec.skills would encode to 70000 bytes as the "
        "HARNESS_SKILLS guest env value, exceeding the sandbox's 65536-byte "
        "limit; trim instructions/descriptions or reduce the number of "
        "skills (temporary limit while skill delivery rides an env var)"
    )
    body = {"error": {"code": 400, "message": message}}
    resources = _make_resources([_FakeResponse(400, body, reason="Bad Request")])

    with pytest.raises(HttpResponseError) as exc_info:
        resources.sessions.create_from_manifest("kind: Agent\nspec:\n  skills: []\n")

    error_text = str(exc_info.value)
    assert message in error_text
    assert '{"error"' not in error_text
    assert '{"message"' not in error_text


def test_get_session_url_encodes_id():
    resources = _make_resources(
        [_FakeResponse(200, {"session": {"session_id": "x/y"}})]
    )
    resources.sessions.get("x/y")

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "GET"
    assert call.request.url.endswith("/v2/agents/sessions/x%2Fy")


def test_get_session_strips_team_id_and_tenant_id():
    body = {
        "session": {
            "session_id": "abc-123",
            "status": SessionStatus.READY,
            "team_id": 10212320,
            "tenant_id": "10212320",
        }
    }
    resources = _make_resources([_FakeResponse(200, body)])

    session = resources.sessions.get("abc-123").session
    assert session.session_id == "abc-123"
    assert "team_id" not in session
    assert "tenant_id" not in session


def test_destroy_session():
    resources = _make_resources([_FakeResponse(200, "")])
    resources.sessions.destroy("abc-123")

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "DELETE"
    assert call.request.url.endswith("/v2/agents/sessions/abc-123")


def test_pause_session():
    resources = _make_resources(
        [_FakeResponse(200, {"session": {"session_id": "abc-123"}})]
    )
    resources.sessions.pause("abc-123")

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "POST"
    assert call.request.url.endswith("/v2/agents/sessions/abc-123/pause")


def test_pause_session_strips_team_id_and_tenant_id():
    body = {
        "session": {
            "session_id": "abc-123",
            "team_id": 10212320,
            "tenant_id": "10212320",
        }
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.sessions.pause("abc-123")

    assert "team_id" not in resp.session
    assert "tenant_id" not in resp.session


def test_resume_session():
    resources = _make_resources(
        [_FakeResponse(200, {"session": {"session_id": "abc-123"}})]
    )
    resources.sessions.resume("abc-123")

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "POST"
    assert call.request.url.endswith("/v2/agents/sessions/abc-123/resume")


def test_resume_session_strips_team_id_and_tenant_id():
    body = {
        "session": {
            "session_id": "abc-123",
            "team_id": 10212320,
            "tenant_id": "10212320",
        }
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.sessions.resume("abc-123")

    assert "team_id" not in resp.session
    assert "tenant_id" not in resp.session


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


def test_list_sessions_filters_by_name():
    resources = _make_resources([_FakeResponse(200, {"sessions": []})])
    resources.sessions.list(name="my-session")

    call = resources._proxy._original._pipeline.calls[0]
    assert "name=my-session" in call.request.url


def test_list_sessions_strips_team_id_and_tenant_id():
    body = {
        "sessions": [
            {
                "session_id": "s1",
                "status": SessionStatus.READY,
                "team_id": 10212320,
                "tenant_id": "10212320",
            },
            {
                "session_id": "s2",
                "status": SessionStatus.PAUSED,
                "team_id": 55,
                "tenant_id": "55",
            },
        ],
        "next_page_token": "",
    }
    resources = _make_resources([_FakeResponse(200, body)])

    sessions = resources.sessions.list().sessions
    assert [session.session_id for session in sessions] == ["s1", "s2"]
    assert all("team_id" not in session for session in sessions)
    assert all("tenant_id" not in session for session in sessions)


def test_attach_by_name_picks_most_recent_match():
    resources = _make_resources(
        [
            _FakeResponse(
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
    agent = resources.attach_by_name("dup")

    assert "name=dup" in resources._proxy._original._pipeline.calls[0].request.url
    assert agent.session_id == "new"


def test_attach_by_name_raises_when_not_found():
    resources = _make_resources([_FakeResponse(200, {"sessions": []})])
    with pytest.raises(LookupError):
        resources.attach_by_name("missing")


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


def test_start_provider_auth():
    body = {
        "provider": "github",
        "status": "pending",
        "connect_url": "https://cloud.digitalocean.com/security/connectlinks/confirm?token=abc",
        "poll_url": "https://cloud.digitalocean.com/api/v1/security/connectlinks/poll?token=def",
        "verification_code": "k5r2cprq",
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.sessions.start_provider_auth(OAuthProvider.GITHUB)

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "POST"
    assert call.request.url.endswith("/v2/agents/auth/github")
    assert json.loads(call.request.content) == {}
    assert resp.status == "pending"
    assert resp.connect_url.endswith("token=abc")


def test_poll_provider_auth():
    body = {"provider": "github", "status": "success"}
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.sessions.poll_provider_auth(
        OAuthProvider.GITHUB,
        "https://cloud.digitalocean.com/api/v1/security/connectlinks/poll?token=def",
    )

    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "GET"
    url = call.request.url
    assert "/v2/agents/auth/github/poll" in url
    assert "poll_url=" in url
    assert resp.status == "success"


def test_poll_provider_auth_requires_poll_url():
    resources = _make_resources([])
    with pytest.raises(ValueError):
        resources.sessions.poll_provider_auth(OAuthProvider.GITHUB, "")


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


def test_stream_drops_tenant_id_from_spi_canonical_events():
    sse_payload = (
        b'data: {"event_id":"e1","tenant_id":"10212320","session_id":"s1",'
        b'"seq":1,"type":"run.token_delta","data":{"text":"hello"}}\n\n'
    )
    resources = _make_resources([_FakeResponse(200, sse_chunks=[sse_payload])])

    event = list(resources.sessions.stream("s1"))[0]
    assert "tenant_id" not in event
    assert "team_id" not in event
    assert event.event_id == "e1"
    assert event.type == "run.token_delta"
    assert event.data.text == "hello"


def test_stream_drops_tenant_id_from_result_envelope():
    sse_payload = (
        b'data: {"result":{"event_id":"e1","tenant_id":"10212320",'
        b'"team_id":10212320,"token_chunk":{"text":"hello"}}}\n\n'
    )
    resources = _make_resources([_FakeResponse(200, sse_chunks=[sse_payload])])

    event = list(resources.sessions.stream("s1"))[0]
    assert "tenant_id" not in event
    assert "team_id" not in event
    assert event.token_chunk.text == "hello"


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


# ---------------------------------------------------------------------------
# Backward history paging
# ---------------------------------------------------------------------------

_HISTORY_PAGE_SSE = (
    b": connected to s1\n\n"
    b'data: {"event_id":"e10","type":"run.token_delta","data":{"text":"older "}}\n\n'
    b'data: {"event_id":"e11","type":"run.token_delta","data":{"text":"newer"}}\n\n'
    b": has_more=true\n\n"
)


def test_stream_before_implies_replay_only_and_sends_limit():
    resources = _make_resources([_FakeResponse(200, sse_chunks=[b""])])

    list(resources.sessions.stream("s1", before="evt-99", limit=50))

    url = resources._proxy._original._pipeline.calls[0].request.url
    assert "before=evt-99" in url
    assert "limit=50" in url
    assert "replay_only=true" in url


def test_stream_omits_paging_params_when_unset():
    resources = _make_resources([_FakeResponse(200, sse_chunks=[b""])])

    list(resources.sessions.stream("s1"))

    url = resources._proxy._original._pipeline.calls[0].request.url
    assert "before=" not in url
    assert "limit=" not in url
    assert "replay_only=" not in url


def test_stream_rejects_limit_without_before():
    resources = _make_resources([])
    with pytest.raises(ValueError, match="before"):
        resources.sessions.stream("s1", limit=10)


@pytest.mark.parametrize("limit", [0, -1])
def test_stream_rejects_non_positive_limit(limit):
    resources = _make_resources([])
    with pytest.raises(ValueError, match="positive"):
        resources.sessions.stream("s1", before="evt-99", limit=limit)


def test_stream_records_has_more_comment():
    resources = _make_resources([_FakeResponse(200, sse_chunks=[_HISTORY_PAGE_SSE])])

    stream = resources.sessions.stream("s1", before="evt-12")
    assert stream.has_more is None  # not known until the trailing comment arrives

    events = list(stream)
    assert [e.event_id for e in events] == ["e10", "e11"]
    assert stream.has_more is True
    assert stream.oldest_event_id == "e10"


def test_stream_ignores_non_has_more_comments():
    payload = (
        b": connected to s1\n\n"
        b'data: {"event_id":"e1","type":"run.started","data":{}}\n\n'
    )
    resources = _make_resources([_FakeResponse(200, sse_chunks=[payload])])

    stream = resources.sessions.stream("s1")
    assert len(list(stream)) == 1
    assert stream.has_more is None


def test_history_page_returns_events_cursor_and_has_more():
    resources = _make_resources([_FakeResponse(200, sse_chunks=[_HISTORY_PAGE_SSE])])

    page = resources.sessions.history_page("s1", before="evt-12", limit=2)

    url = resources._proxy._original._pipeline.calls[0].request.url
    assert "before=evt-12" in url
    assert "limit=2" in url
    assert "replay_only=true" in url

    events, has_more, next_before = page
    assert [e.event_id for e in events] == ["e10", "e11"]
    assert has_more is True
    assert next_before == "e10"


def test_history_page_at_oldest_event_reports_no_more():
    payload = (
        b'data: {"event_id":"e1","type":"run.started","data":{}}\n\n'
        b": has_more=false\n\n"
    )
    resources = _make_resources([_FakeResponse(200, sse_chunks=[payload])])

    page = resources.sessions.history_page("s1", before="e2")
    assert page.has_more is False
    assert page.next_before == "e1"


def test_history_page_empty_has_no_cursor():
    payload = b": has_more=false\n\n"
    resources = _make_resources([_FakeResponse(200, sse_chunks=[payload])])

    page = resources.sessions.history_page("s1", before="e1")
    assert page.events == []
    assert page.has_more is False
    assert page.next_before is None


def test_history_page_requires_before():
    resources = _make_resources([])
    with pytest.raises(ValueError, match="before"):
        resources.sessions.history_page("s1", before="")


def test_agent_session_history_binds_session_id():
    resources = _make_resources([_FakeResponse(200, sse_chunks=[_HISTORY_PAGE_SSE])])

    page = resources.attach("s1").history(before="evt-12")

    url = resources._proxy._original._pipeline.calls[0].request.url
    assert "/v2/agents/sessions/s1/stream" in url
    assert "before=evt-12" in url
    assert page.next_before == "e10"


def test_resolve_agents_base_url_adds_https_scheme():
    assert (
        resolve_agents_base_url("api.digitalocean.com")
        == "https://api.digitalocean.com"
    )
    assert resolve_agents_base_url("http://127.0.0.1:8080") == "http://127.0.0.1:8080"
