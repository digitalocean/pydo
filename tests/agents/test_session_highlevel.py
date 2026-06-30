# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for the high-level agent interface (:mod:`pydo.agents.session`)."""
from __future__ import annotations

from typing import Any, List

import pytest

from pydo.agents import AgentEvent, AgentEventType, AgentSession, RunResult
from pydo.agents.custom_models import HITLOutcome
from pydo.aio.agents import AsyncAgentSession


# ---------------------------------------------------------------------------
# Sync fakes
# ---------------------------------------------------------------------------


class _FakeRawStream:
    def __init__(self, events: List[dict]):
        self._events = events
        self.closed = False

    def __iter__(self):
        return iter(self._events)

    def close(self):
        self.closed = True


class _FakeSessions:
    """Stands in for SessionsOperations, recording call order."""

    def __init__(self, events: List[dict]):
        self._events = events
        self.calls: List[Any] = []
        self.resolved: List[Any] = []
        self.destroyed = False

    def create_from_manifest(self, manifest):
        self.calls.append(("create", manifest))
        return {"session": {"session_id": "s1", "status": "SESSION_STATUS_READY"}}

    def stream(self, session_id, **kwargs):
        self.calls.append(("stream", session_id))
        return _FakeRawStream(self._events)

    def send_input(self, session_id, *, text):
        self.calls.append(("send_input", session_id, text))
        return {"run_id": "r1"}

    def resolve_hitl(
        self, session_id, request_id, *, outcome, reason=None, source=None
    ):
        self.calls.append(("resolve_hitl", session_id, request_id, outcome))
        self.resolved.append((request_id, outcome))

    def get(self, session_id):
        return {"session": {"session_id": session_id, "status": "SESSION_STATUS_READY"}}

    def destroy(self, session_id):
        self.calls.append(("destroy", session_id))
        self.destroyed = True


# ---------------------------------------------------------------------------
# AgentEvent normalization
# ---------------------------------------------------------------------------


def test_agent_event_normalizes_token():
    ev = AgentEvent({"type": "run.token_delta", "data": {"text": "hi"}, "run_id": "r1"})
    assert ev.type == AgentEventType.TOKEN
    assert ev.text == "hi"
    assert ev.run_id == "r1"


def test_agent_event_normalizes_completed_and_failed():
    done = AgentEvent({"type": "run.completed", "data": {"total_tokens_out": 7}})
    assert done.type == AgentEventType.COMPLETED
    assert done.usage["tokens_out"] == 7

    failed = AgentEvent({"type": "run.failed", "data": {"code": 3, "message": "boom"}})
    assert failed.type == AgentEventType.FAILED
    assert failed.error == {"code": 3, "message": "boom"}


def test_agent_event_unknown_type_is_other():
    assert AgentEvent({"type": "session.updated"}).type == AgentEventType.OTHER


# ---------------------------------------------------------------------------
# run / run_streamed
# ---------------------------------------------------------------------------


def test_run_collects_final_output_usage_and_order():
    events = [
        {"type": "run.started", "data": {}},
        {"type": "run.token_delta", "data": {"text": "Hello "}},
        {"type": "run.token_delta", "data": {"text": "world"}},
        {
            "type": "run.completed",
            "data": {
                "total_tokens_in": 3,
                "total_tokens_out": 5,
                "run_cost_micros": 1234,
            },
        },
    ]
    sessions = _FakeSessions(events)
    result = AgentSession(sessions, "s1").run("hi")

    assert isinstance(result, RunResult)
    assert result.final_output == "Hello world"
    assert result.status == "completed" and result.ok
    assert result.usage["tokens_out"] == 5
    assert result.run_id == "r1"
    # stream is opened BEFORE input is sent (so no early events are missed)
    kinds = [c[0] for c in sessions.calls]
    assert kinds.index("stream") < kinds.index("send_input")


def test_run_streamed_yields_typed_events():
    events = [
        {"type": "run.token_delta", "data": {"text": "hi"}},
        {"type": "run.completed", "data": {}},
    ]
    stream = AgentSession(_FakeSessions(events), "s1").run_streamed("x")
    seen = [e.type for e in stream]
    assert seen == [AgentEventType.TOKEN, AgentEventType.COMPLETED]
    assert stream.final_output == "hi"
    assert stream.status == "completed"


def test_run_failed_sets_status_and_error():
    events = [
        {"type": "run.token_delta", "data": {"text": "partial"}},
        {"type": "run.failed", "data": {"code": 3, "message": "boom"}},
    ]
    result = AgentSession(_FakeSessions(events), "s1").run("x")
    assert result.status == "failed" and not result.ok
    assert result.error["message"] == "boom"


# ---------------------------------------------------------------------------
# HITL policy
# ---------------------------------------------------------------------------


def test_run_auto_approves_hitl_by_default():
    events = [
        {"type": "run.human_input_requested", "data": {"hitl_id": "req-1"}},
        {"type": "run.token_delta", "data": {"text": "done"}},
        {"type": "run.completed", "data": {}},
    ]
    sessions = _FakeSessions(events)
    result = AgentSession(sessions, "s1").run("do it")
    assert ("req-1", HITLOutcome.APPROVE) in sessions.resolved
    assert result.final_output == "done"


def test_hitl_callable_policy_receives_event():
    events = [
        {"type": "run.human_input_requested", "data": {"hitl_id": "req-9"}},
        {"type": "run.completed", "data": {}},
    ]
    sessions = _FakeSessions(events)
    seen = []

    def policy(event):
        seen.append(event.request_id)
        return "reject"

    AgentSession(sessions, "s1").run("x", hitl=policy)
    assert seen == ["req-9"]
    assert ("req-9", HITLOutcome.REJECT) in sessions.resolved


def test_hitl_none_leaves_prompt_unresolved():
    events = [
        {"type": "run.human_input_requested", "data": {"hitl_id": "req-9"}},
        {"type": "run.completed", "data": {}},
    ]
    sessions = _FakeSessions(events)
    AgentSession(sessions, "s1").run("x", hitl=None)
    assert sessions.resolved == []


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_context_manager_destroys():
    sessions = _FakeSessions([])
    with AgentSession(sessions, "s1") as agent:
        assert agent.session_id == "s1"
    assert sessions.destroyed


def test_run_stream_closes_underlying_stream():
    events = [{"type": "run.completed", "data": {}}]
    sessions = _FakeSessions(events)
    stream = AgentSession(sessions, "s1").run_streamed("x")
    raw = stream._raw
    list(stream)
    assert raw.closed


# ---------------------------------------------------------------------------
# Async parity
# ---------------------------------------------------------------------------


class _FakeAsyncRawStream:
    def __init__(self, events: List[dict]):
        self._events = events
        self.closed = False

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for ev in self._events:
            yield ev

    async def close(self):
        self.closed = True


class _FakeAsyncSessions:
    def __init__(self, events: List[dict]):
        self._events = events
        self.calls: List[Any] = []
        self.resolved: List[Any] = []
        self.destroyed = False

    async def stream(self, session_id, **kwargs):
        self.calls.append(("stream", session_id))
        return _FakeAsyncRawStream(self._events)

    async def send_input(self, session_id, *, text):
        self.calls.append(("send_input", session_id, text))
        return {"run_id": "r1"}

    async def resolve_hitl(
        self, session_id, request_id, *, outcome, reason=None, source=None
    ):
        self.resolved.append((request_id, outcome))

    async def destroy(self, session_id):
        self.destroyed = True


@pytest.mark.asyncio
async def test_async_run_collects_output_and_order():
    events = [
        {"type": "run.token_delta", "data": {"text": "Hi "}},
        {"type": "run.token_delta", "data": {"text": "there"}},
        {"type": "run.completed", "data": {"total_tokens_out": 2}},
    ]
    sessions = _FakeAsyncSessions(events)
    result = await AsyncAgentSession(sessions, "s1").run("x")
    assert result.final_output == "Hi there"
    assert result.status == "completed"
    assert result.usage["tokens_out"] == 2
    kinds = [c[0] for c in sessions.calls]
    assert kinds.index("stream") < kinds.index("send_input")


@pytest.mark.asyncio
async def test_async_auto_approves_hitl():
    events = [
        {"type": "run.human_input_requested", "data": {"hitl_id": "req-1"}},
        {"type": "run.completed", "data": {}},
    ]
    sessions = _FakeAsyncSessions(events)
    await AsyncAgentSession(sessions, "s1").run("x")
    assert ("req-1", HITLOutcome.APPROVE) in sessions.resolved


@pytest.mark.asyncio
async def test_async_context_manager_destroys():
    sessions = _FakeAsyncSessions([])
    async with AsyncAgentSession(sessions, "s1") as agent:
        assert agent.session_id == "s1"
    assert sessions.destroyed
