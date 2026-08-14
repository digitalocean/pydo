#!/usr/bin/env python3
"""Smoke-test the OpenAI Agents sandbox-provider feature in pydo.

Modes
-----
  offline (default if DIGITALOCEAN_TOKEN / OPENAI_API_KEY missing):
    Exercises manifest detection, placeholder resolution, and
    create_from_manifest query-param wiring with mocks — no network.

  live (both tokens set, or --live):
    Full doctl-equivalent flow against a real harness + OpenAI:
      1. client.agents.start(manifest)  → OpenAI session + DO sandbox
      2. wait_until_ready
      3. agent.run(...)                 → bridges to OpenAI (not DO SSE)
      4. destroy on exit

Required for live:
  DIGITALOCEAN_TOKEN
  OPENAI_API_KEY
  PYDO_AGENTS_ENDPOINT   optional (e.g. https://api.s2r1.internal.digitalocean.com)
  AGENT_SPEC             optional path to agents.yaml
  PROMPT                 optional override for the run prompt

Examples:
  python examples/agents/test_openai_sandbox_feature.py
  python examples/agents/test_openai_sandbox_feature.py --live
  AGENT_SPEC=./openai-agents.yaml python examples/agents/test_openai_sandbox_feature.py --live
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock, patch

# Allow running from repo root without installing an editable package.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SRC = os.path.join(_REPO_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# Default config next to this script.
DEFAULT_SPEC_PATH = os.path.join(os.path.dirname(__file__), "openai-agents.yaml")

from pydo.agents import (  # noqa: E402
    AgentKind,
    AgentsResources,
    AgentSession,
    SessionStatus,
    is_openai_codex_manifest,
    is_openai_codex_session,
    prepare_openai_codex_manifest,
    resolve_placeholders,
)
from pydo.agents.custom_openai_sandbox import (  # noqa: E402
    extract_openai_create_body,
    load_manifest_doc,
)


def _load_manifest(path: str | None) -> str:
    """Load agents.yaml from *path*, defaulting to ``openai-agents.yaml``."""
    resolved = path or DEFAULT_SPEC_PATH
    if not os.path.exists(resolved):
        raise FileNotFoundError(
            f"manifest not found: {resolved}\n"
            f"Create it or set AGENT_SPEC=/path/to/agents.yaml"
        )
    with open(resolved, "r", encoding="utf-8") as fh:
        text = fh.read()
    print(f"[manifest] {resolved}", file=sys.stderr)
    return text


def _ok(label: str) -> None:
    print(f"  PASS  {label}")


def _fail(label: str, detail: str) -> None:
    print(f"  FAIL  {label}: {detail}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Offline checks (no network)
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int, body: Any = None):
        self.status_code = status_code
        if isinstance(body, (dict, list)):
            self._body = json.dumps(body).encode("utf-8")
        else:
            self._body = b""

    def text(self) -> str:
        return self._body.decode("utf-8")

    def body(self) -> bytes:
        return self._body

    def read(self) -> bytes:
        return self._body

    def close(self) -> None:
        return None


class _FakePipeline:
    def __init__(self, responses: List[_FakeResponse]):
        self._responses = list(responses)
        self.calls: List[Any] = []

    def run(self, request, *, stream=False, **kwargs):
        self.calls.append(SimpleNamespace(request=request, stream=stream, kwargs=kwargs))
        return SimpleNamespace(http_response=self._responses.pop(0))


def run_offline(manifest: str) -> int:
    print("=== offline: OpenAI sandbox-provider smoke ===")
    failures = 0

    try:
        import yaml  # noqa: F401
    except ImportError:
        _fail("PyYAML installed", "pip install 'pydo[agents-openai]' or PyYAML")
        return 1
    _ok("PyYAML installed")

    doc = load_manifest_doc(manifest)
    if not is_openai_codex_manifest(doc):
        _fail("manifest detected as OpenAI codex", "adapter/spec.openai missing")
        failures += 1
    else:
        _ok("manifest detected as OpenAI codex")

    body = extract_openai_create_body(doc)
    if body.get("environment", {}).get("type") != "self_hosted":
        _fail("extract openai body", f"unexpected body keys={list(body)}")
        failures += 1
    else:
        _ok(f"extract openai body (model={body.get('agent', {}).get('model')})")

    resolved = resolve_placeholders(
        "env=${ENV_ID} key=${OPENAI_API_KEY}",
        {"ENV_ID": "env_demo", "OPENAI_API_KEY": "sk-demo"},
    )
    if resolved != "env=env_demo key=sk-demo":
        _fail("placeholder resolution", resolved)
        failures += 1
    else:
        _ok("placeholder resolution")

    prepared, sess, env = prepare_openai_codex_manifest(
        manifest,
        openai_api_key="sk-demo",
        openai_session_id="sess_demo",
        openai_environment_id="env_demo",
    )
    if "${ENV_ID}" in prepared or "${OPENAI_API_KEY}" in prepared:
        _fail("prepare_openai_codex_manifest", "placeholders still present")
        failures += 1
    elif sess != "sess_demo" or env != "env_demo":
        _fail("prepare_openai_codex_manifest", f"ids={sess},{env}")
        failures += 1
    else:
        _ok("prepare_openai_codex_manifest (known ids)")

    if not is_openai_codex_session(
        {"agent_kind": AgentKind.OPENAI_CODEX, "openai_session_id": "sess_x"}
    ):
        _fail("session discriminator", "OPENAI_CODEX not recognized")
        failures += 1
    else:
        _ok("session discriminator (AGENT_KIND_OPENAI_CODEX)")

    # create_from_manifest must send openai_session_id as a query param.
    parent = MagicMock()
    parent._client = MagicMock()
    parent._client._pipeline = _FakePipeline(
        [
            _FakeResponse(
                200,
                {
                    "session": {
                        "session_id": "do-1",
                        "status": SessionStatus.READY,
                        "agent_kind": AgentKind.OPENAI_CODEX,
                        "openai_session_id": "sess_demo",
                        "openai_environment_id": "env_demo",
                    }
                },
            )
        ]
    )
    resources = AgentsResources(parent, agents_endpoint="https://api.example.com")
    resources.sessions.create_from_manifest(
        prepared, openai_session_id="sess_demo"
    )
    url = resources._proxy._original._pipeline.calls[0].request.url
    if "openai_session_id=sess_demo" not in url:
        _fail("create_from_manifest query param", url)
        failures += 1
    else:
        _ok("create_from_manifest passes openai_session_id query param")

    # run() must bridge to OpenAI, not DO stream/send_input.
    sessions = MagicMock()
    sessions.get.return_value = {
        "session": {
            "session_id": "do-1",
            "agent_kind": AgentKind.OPENAI_CODEX,
            "openai_session_id": "sess_demo",
            "status": SessionStatus.READY,
        }
    }
    agent = AgentSession(sessions, "do-1", openai_api_key="sk-demo")
    agent.refresh()
    fake_events = [
        {"type": "response.output_text.delta", "delta": "hello "},
        {"type": "response.output_text.delta", "delta": "from openai"},
        {"type": "response.completed"},
    ]
    with patch(
        "pydo.agents.session.send_openai_session_input", return_value={}
    ) as send, patch(
        "pydo.agents.session.stream_openai_session_events",
        return_value=iter(fake_events),
    ):
        result = agent.run("ping")
    if sessions.stream.called or sessions.send_input.called:
        _fail("OpenAI run bridge", "DO stream/send_input was called")
        failures += 1
    elif not send.called or result.final_output != "hello from openai":
        _fail("OpenAI run bridge", f"output={result.final_output!r}")
        failures += 1
    else:
        _ok("agent.run bridges to OpenAI (skips DO SSE)")

    print()
    if failures:
        print(f"offline: {failures} failure(s)")
        return 1
    print("offline: all checks passed")
    print("Tip: set DIGITALOCEAN_TOKEN + OPENAI_API_KEY and re-run with --live")
    return 0


# ---------------------------------------------------------------------------
# Live e2e
# ---------------------------------------------------------------------------


def run_live(manifest: str, prompt: str) -> int:
    print("=== live: OpenAI sandbox-provider e2e ===")
    token = os.environ.get("DIGITALOCEAN_TOKEN")
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not token or not openai_key:
        print(
            "DIGITALOCEAN_TOKEN and OPENAI_API_KEY are required for --live",
            file=sys.stderr,
        )
        return 2

    from pydo import Client

    endpoint = os.environ.get("PYDO_AGENTS_ENDPOINT")
    client = Client(token=token, agents_endpoint=endpoint)
    print(f"agents endpoint: {client.agents.base_url}", file=sys.stderr)

    with client.agents.start(manifest, openai_api_key=openai_key) as agent:
        print(
            f"[create] do={agent.session_id} openai={agent.openai_session_id} "
            f"env={agent.openai_environment_id} kind={agent.agent_kind}",
            file=sys.stderr,
        )
        if not agent.is_openai_codex:
            print(
                f"expected OpenAI codex session, got kind={agent.agent_kind!r}",
                file=sys.stderr,
            )
            return 1

        agent.wait_until_ready(timeout=180.0)
        print(f"[ready] status={agent.status}", file=sys.stderr)
        print(f"[run] prompt={prompt!r}", file=sys.stderr)
        result = agent.run(prompt, timeout=300.0)
        print(f"[done] status={result.status} ok={result.ok}", file=sys.stderr)
        print(result.final_output or "(empty output)")
        return 0 if result.ok else 1


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Hit real DO + OpenAI APIs (requires tokens)",
    )
    parser.add_argument(
        "--prompt",
        default=os.environ.get("PROMPT", "List files in /workspace"),
        help="Prompt used in live mode",
    )
    parser.add_argument(
        "--spec",
        default=os.environ.get("AGENT_SPEC") or DEFAULT_SPEC_PATH,
        help=f"Path to agents.yaml (default: {DEFAULT_SPEC_PATH})",
    )
    args = parser.parse_args(argv)

    manifest = _load_manifest(args.spec)

    has_tokens = bool(
        os.environ.get("DIGITALOCEAN_TOKEN") and os.environ.get("OPENAI_API_KEY")
    )
    if args.live or os.environ.get("PYDO_OPENAI_LIVE") == "1":
        return run_live(manifest, args.prompt)
    if has_tokens:
        print(
            "[info] tokens detected; pass --live (or PYDO_OPENAI_LIVE=1) for e2e",
            file=sys.stderr,
        )
    return run_offline(manifest)


if __name__ == "__main__":
    raise SystemExit(main())
