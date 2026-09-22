"""Policy engine test: auto-allow rule.

Creates a session with ``defaultAction: ask`` and a single ``touch * → allow``
rule, then asks the agent to run ``touch /workspace/allow_test.txt``.

Expected: the Bash tool call matches the allow rule and executes WITHOUT any
HITL prompt being raised. The test FAILS if a ``hitl_requested`` event fires.

Required env:
  DIGITALOCEAN_TOKEN
  AGENT_SPEC   path to the base agents.yaml (default: agent-spec.yaml)

Optional env:
  PYDO_AGENTS_ENDPOINT   stage2: https://api.s2r1.internal.digitalocean.com
"""

import os
import sys

import yaml

from pydo import Client
from pydo.agents import AgentEventType


_PERMISSIONS = {
    "defaultAction": "ask",
    "rules": [
        {"tool": "bash", "match": {"command": "touch *"}, "action": "allow"},
        {"tool": "bash", "match": {"command": "git status"}, "action": "allow"},
    ],
}

_PROMPT = (
    "Use bash to run exactly this command and nothing else: "
    "touch /workspace/allow_test.txt"
)


def _load_manifest(name: str, permissions: dict) -> str:
    spec_path = os.environ.get("AGENT_SPEC", "agent-spec.yaml")
    with open(spec_path, "r", encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    spec["metadata"]["name"] = name
    spec["spec"]["permissions"] = permissions
    return yaml.dump(spec, default_flow_style=False)


def main() -> int:
    client = Client(
        token=os.environ["DIGITALOCEAN_TOKEN"],
        agents_endpoint=os.environ.get("PYDO_AGENTS_ENDPOINT"),
    )

    manifest = _load_manifest("policy-auto-allow-test", _PERMISSIONS)
    hitl_events = []

    def _track_and_approve(event):
        hitl_events.append(event)
        return "approve"  # resolve so the run doesn't hang if HITL fires unexpectedly

    with client.agents.start(manifest) as agent:
        print(f"[session {agent.session_id}]", file=sys.stderr)
        print(f"[policy] defaultAction=ask  touch * → allow", file=sys.stderr)
        print(f"[prompt] {_PROMPT}\n", file=sys.stderr)

        stream = agent.run_streamed(_PROMPT, hitl=_track_and_approve, timeout=180)
        for event in stream:
            if event.type == AgentEventType.TOKEN:
                print(event.text, end="", flush=True)
            elif event.type == AgentEventType.TOOL_CALL:
                print(f"\n[tool_call] {event.tool_name}", file=sys.stderr)
            elif event.type == AgentEventType.HITL_REQUESTED:
                print(f"\n[hitl_fired] request_id={event.request_id}", file=sys.stderr)

        result = stream.result
        print(f"\n[{result.status}]", file=sys.stderr)

    if hitl_events:
        print(
            f"\nFAIL HITL fired {len(hitl_events)} time(s) — "
            "touch should have been auto-allowed without prompting",
            file=sys.stderr,
        )
        return 1

    if result.status != "completed":
        print(
            f"\nFAIL run ended with status={result.status!r}",
            file=sys.stderr,
        )
        return 1

    print("\nPASS touch ran without HITL prompt (auto-allow confirmed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
