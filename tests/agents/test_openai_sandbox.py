# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for OpenAI Agents sandbox-provider helpers."""
from __future__ import annotations

import json
import threading
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest

from pydo.agents import (
    AgentKind,
    AgentsResources,
    AgentSession,
    SessionStatus,
    is_openai_codex_session,
    prepare_openai_codex_manifest,
    resolve_placeholders,
)
from pydo.agents.custom_openai_sandbox import (
    extract_openai_create_body,
    is_openai_codex_manifest,
    load_manifest_doc,
)

yaml = pytest.importorskip("yaml")


_OPENAI_MANIFEST = """\
apiVersion: agents.digitalocean.com/v1alpha1
kind: Agent
metadata:
  name: openai-codex-session
spec:
  runtime:
    adapter: openai-agent-codex
  sandbox:
    idleTimeoutSeconds: 2700
  env:
    CODEX_ENVIRONMENT_ID: ${ENV_ID}
    CODEX_API_KEY: ${OPENAI_API_KEY}
  secrets:
    - name: CODEX_API_KEY
      source: tenantSecret
  openai:
    agent:
      model: gpt-5.6-sol
      instructions: "Answer clearly."
    environment:
      type: self_hosted
      workspace_directory: /workspace
    input:
      - role: user
        content:
          - type: input_text
            text: "hello"
"""


class _FakeResponse:
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

    def text(self) -> str:
        return self._body_bytes.decode("utf-8")

    def body(self) -> bytes:
        return self._body_bytes

    def read(self) -> bytes:
        return self._body_bytes

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


def test_agent_kind_openai_codex_constant():
    assert AgentKind.OPENAI_CODEX == "AGENT_KIND_OPENAI_CODEX"


def test_is_openai_codex_manifest_and_extract_body():
    doc = load_manifest_doc(_OPENAI_MANIFEST)
    assert is_openai_codex_manifest(doc)
    body = extract_openai_create_body(doc)
    assert body["agent"]["model"] == "gpt-5.6-sol"
    assert body["environment"]["type"] == "self_hosted"


def test_is_openai_codex_session_discriminator():
    assert is_openai_codex_session(
        {"agent_kind": AgentKind.OPENAI_CODEX, "openai_session_id": ""}
    )
    assert is_openai_codex_session({"openai_session_id": "sess_abc"})
    assert not is_openai_codex_session({"agent_kind": AgentKind.CLAUDE_CODE})


def test_resolve_placeholders_prefers_explicit_map():
    text = "id=${ENV_ID} key=${OPENAI_API_KEY} other=${HOME}"
    out = resolve_placeholders(
        text,
        {"ENV_ID": "env_1", "OPENAI_API_KEY": "sk-test"},
        environ={"HOME": "/tmp", "OPENAI_API_KEY": "sk-env"},
    )
    assert out == "id=env_1 key=sk-test other=/tmp"


def test_prepare_openai_codex_manifest_with_known_ids():
    resolved, session_id, env_id = prepare_openai_codex_manifest(
        _OPENAI_MANIFEST,
        openai_api_key="sk-test",
        openai_session_id="sess_known",
        openai_environment_id="env_known",
    )
    assert session_id == "sess_known"
    assert env_id == "env_known"
    assert "env_known" in resolved
    assert "sk-test" in resolved
    assert "${ENV_ID}" not in resolved
    assert "${OPENAI_API_KEY}" not in resolved


def test_prepare_creates_openai_session_when_ids_missing():
    fake_payload = {
        "session_id": "sess_new",
        "environment": {"environment_id": "env_new"},
    }
    with patch(
        "pydo.agents.custom_openai_sandbox.create_openai_agents_session",
        return_value=("sess_new", "env_new", fake_payload),
    ) as create:
        resolved, session_id, env_id = prepare_openai_codex_manifest(
            _OPENAI_MANIFEST,
            openai_api_key="sk-test",
        )
    create.assert_called_once()
    assert session_id == "sess_new"
    assert env_id == "env_new"
    assert "CODEX_ENVIRONMENT_ID: env_new" in resolved


def test_create_from_manifest_passes_openai_session_id_query_param():
    body = {
        "session": {
            "session_id": "do-1",
            "status": SessionStatus.READY,
            "agent_kind": AgentKind.OPENAI_CODEX,
            "openai_session_id": "sess_abc",
            "openai_environment_id": "env_abc",
        }
    }
    resources = _make_resources([_FakeResponse(200, body)])
    resources.sessions.create_from_manifest(
        "kind: Agent\n",
        openai_session_id="sess_abc",
    )
    call = resources._proxy._original._pipeline.calls[0]
    assert "openai_session_id=sess_abc" in call.request.url


def test_start_orchestrates_openai_then_creates_do_session():
    body = {
        "session": {
            "session_id": "do-1",
            "status": SessionStatus.READY,
            "agent_kind": AgentKind.OPENAI_CODEX,
            "openai_session_id": "sess_oai",
            "openai_environment_id": "env_oai",
        }
    }
    resources = _make_resources([_FakeResponse(200, body)])
    with patch(
        "pydo.agents.prepare_openai_codex_manifest",
        return_value=("resolved-yaml", "sess_oai", "env_oai"),
    ) as prepare:
        agent = resources.start(_OPENAI_MANIFEST, openai_api_key="sk-test")

    prepare.assert_called_once()
    call = resources._proxy._original._pipeline.calls[0]
    assert call.request.method == "POST"
    assert "openai_session_id=sess_oai" in call.request.url
    content = call.request.content
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    assert content == "resolved-yaml"
    assert agent.session_id == "do-1"
    assert agent.is_openai_codex
    assert agent.openai_session_id == "sess_oai"


def test_agent_session_run_bridges_to_openai_not_do_stream():
    sessions = MagicMock()
    sessions.get.return_value = {
        "session": {
            "session_id": "do-1",
            "agent_kind": AgentKind.OPENAI_CODEX,
            "openai_session_id": "sess_oai",
            "status": SessionStatus.READY,
        }
    }
    agent = AgentSession(sessions, "do-1", openai_api_key="sk-test")
    agent.refresh()

    history = [
        {"type": "session.turn.output_text.delta", "delta": "SEED "},
        {"type": "session.turn.completed"},
    ]
    live = [
        {"type": "session.turn.created"},
        {"type": "session.turn.output_text.delta", "delta": "Hi "},
        {"type": "session.turn.output_text.delta", "delta": "there"},
        {"type": "session.turn.completed"},
    ]
    armed = threading.Event()

    def _fake_stream(*_a, **_k):
        def _gen():
            for event in history:
                yield event
            assert armed.wait(2.0), "send never armed the turn"
            for event in live:
                yield event

        return _gen()

    def _fake_send(*_a, **kwargs):
        cb = kwargs.get("on_request_sent")
        if cb:
            cb()
        armed.set()
        return {}

    with patch(
        "pydo.agents.session.send_openai_session_input", side_effect=_fake_send
    ) as send, patch(
        "pydo.agents.session.stream_openai_session_events", side_effect=_fake_stream
    ):
        result = agent.run("hello")

    send.assert_called_once()
    sessions.stream.assert_not_called()
    sessions.send_input.assert_not_called()
    assert result.final_output == "Hi there"
    assert result.ok
