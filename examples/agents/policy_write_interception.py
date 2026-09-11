"""Policy engine test: non-Bash tool interception (Write/Edit).

Creates a session with ``defaultAction: ask`` (no explicit bash rules) and asks
the agent to write a file. Codex uses its Write tool (not bash) for this, so
the interception exercises the non-Bash tool path of the policy engine.

Expected: a ``hitl_requested`` event fires for the Write/Edit tool call.
The test FAILS if no HITL prompt is raised.

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
    # No rules → every tool call (Bash, Write, Edit, …) requires approval
}

_PROMPT = (
    "Write the text 'policy engine write interception test' into the file "
    "/workspace/write_intercept_test.txt using your file-write capability "
    "(not bash). Do not use bash."
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

    manifest = _load_manifest("policy-write-intercept-test", _PERMISSIONS)
    hitl_events = []
    tool_calls = []

    def _track_and_approve(event):
        hitl_events.append(event)
        print(f"\n[hitl_fired] request_id={event.request_id}", file=sys.stderr)
        return "approve"

    with client.agents.start(manifest) as agent:
        print(f"[session {agent.session_id}]", file=sys.stderr)
        print(f"[policy] defaultAction=ask  (no rules — all tools intercepted)", file=sys.stderr)
        print(f"[prompt] {_PROMPT}\n", file=sys.stderr)

        stream = agent.run_streamed(_PROMPT, hitl=_track_and_approve, timeout=180)
        for event in stream:
            if event.type == AgentEventType.TOKEN:
                print(event.text, end="", flush=True)
            elif event.type == AgentEventType.TOOL_CALL:
                tool_calls.append(event.tool_name)
                print(f"\n[tool_call] {event.tool_name}", file=sys.stderr)
            elif event.type == AgentEventType.HITL_REQUESTED:
                pass  # already logged in the callback

        result = stream.result
        print(f"\n[{result.status}] tool_calls={tool_calls}", file=sys.stderr)

    if not hitl_events:
        print(
            "\nFAIL no HITL event fired — Write/Edit tool should have been "
            "intercepted by defaultAction: ask",
            file=sys.stderr,
        )
        return 1

    if result.status != "completed":
        print(
            f"\nFAIL run ended with status={result.status!r}",
            file=sys.stderr,
        )
        return 1

    print(
        f"\nPASS Write/Edit tool intercepted by policy engine "
        f"({len(hitl_events)} HITL event(s) fired, tool_calls={tool_calls})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
