"""Policy engine test: defaultAction: ask → HITL.

Runs two sub-tests against a session with ``defaultAction: ask`` and no rule
matching ``mkdir``:

  Sub-test approve:
    Agent tries ``mkdir /workspace/hitl_dir``.
    Expected: HITL prompt fires → we approve → run completes.

  Sub-test reject:
    Same prompt on a fresh session.
    Expected: HITL prompt fires → we reject → agent acknowledges denial, run
    completes (agent continues the conversation after the rejection).

Both sub-tests FAIL if no ``hitl_requested`` event fires, or if the run ends in
a non-completed state.

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
        # touch is explicitly allowed so the agent can set up; mkdir is unmatched → ask
        {"tool": "bash", "match": {"command": "touch *"}, "action": "allow"},
        {"tool": "bash", "match": {"command": "git status"}, "action": "allow"},
    ],
}

_PROMPT = (
    "Use bash to run exactly this command and nothing else: "
    "mkdir /workspace/hitl_test_dir"
)


def _load_manifest(name: str, permissions: dict) -> str:
    spec_path = os.environ.get("AGENT_SPEC", "agent-spec.yaml")
    with open(spec_path, "r", encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    spec["metadata"]["name"] = name
    spec["spec"]["permissions"] = permissions
    return yaml.dump(spec, default_flow_style=False)


def _run_hitl_subtest(client, manifest_name: str, decision: str, label: str) -> int:
    """Run one HITL sub-test, resolving HITL with ``decision`` (approve/reject)."""
    manifest = _load_manifest(manifest_name, _PERMISSIONS)
    hitl_events = []

    def _track_and_decide(event):
        hitl_events.append(event)
        print(f"\n[hitl_{decision}] request_id={event.request_id}", file=sys.stderr)
        return decision

    with client.agents.start(manifest) as agent:
        print(f"\n[{label}] session={agent.session_id}", file=sys.stderr)
        print(f"[{label}] prompt: {_PROMPT}", file=sys.stderr)

        stream = agent.run_streamed(_PROMPT, hitl=_track_and_decide, timeout=180)
        for event in stream:
            if event.type == AgentEventType.TOKEN:
                print(event.text, end="", flush=True)
            elif event.type == AgentEventType.TOOL_CALL:
                print(f"\n[tool_call] {event.tool_name}", file=sys.stderr)

        result = stream.result
        print(f"\n[{result.status}]", file=sys.stderr)

    if not hitl_events:
        print(
            f"\nFAIL [{label}] no HITL event fired — "
            "mkdir should have been gated by defaultAction: ask",
            file=sys.stderr,
        )
        return 1

    if result.status != "completed":
        print(
            f"\nFAIL [{label}] run ended with status={result.status!r} "
            f"(expected 'completed')",
            file=sys.stderr,
        )
        return 1

    print(f"\nPASS [{label}] HITL fired and was {decision}d, run completed")
    return 0


def main() -> int:
    client = Client(
        token=os.environ["DIGITALOCEAN_TOKEN"],
        agents_endpoint=os.environ.get("PYDO_AGENTS_ENDPOINT"),
    )

    print("[policy] defaultAction=ask  touch * → allow  mkdir → unmatched", file=sys.stderr)

    rc_a = _run_hitl_subtest(
        client,
        manifest_name="policy-hitl-approve-test",
        decision="approve",
        label="approve",
    )

    rc_b = _run_hitl_subtest(
        client,
        manifest_name="policy-hitl-reject-test",
        decision="reject",
        label="reject",
    )

    return max(rc_a, rc_b)


if __name__ == "__main__":
    raise SystemExit(main())
