"""End-to-end hosted-agents demo: create -> attach -> destroy.

Uses pydo's high-level agent interface, so consuming the SSE feed needs no
manual wiring — no background thread, no completion event, no dispatching on
raw ``run.*`` event strings, and no explicit teardown:

  * ``client.agents.start(manifest)`` creates the session and returns a handle
    that auto-destroys when the ``with`` block exits.
  * ``agent.run_streamed(prompt)`` opens the stream, sends the prompt, and
    yields normalized, typed events (auto-approving HITL prompts by default).
  * ``agent.run(prompt)`` is the blocking one-liner equivalent.

Required env:
  DIGITALOCEAN_TOKEN
  PYDO_AGENTS_ENDPOINT   stage2: https://api.s2r1.internal.digitalocean.com
  AGENT_SPEC             path to the agent spec YAML (agents.yaml manifest)

Optional env:
  PROMPT                 message to send (default: a short demo prompt)
"""

import os
import sys

from pydo import Client
from pydo.agents import AgentEventType


def main():
    spec_path = os.environ.get("AGENT_SPEC", "agent-spec.yaml")
    with open(spec_path, "r", encoding="utf-8") as fh:
        manifest = fh.read()

    prompt = os.environ.get("PROMPT", "In one short sentence, what is DigitalOcean?")

    client = Client(
        token=os.environ["DIGITALOCEAN_TOKEN"],
        agents_endpoint=os.environ.get("PYDO_AGENTS_ENDPOINT"),
    )

    # create + auto-destroy via the context manager.
    with client.agents.start(manifest) as agent:
        print(f"[session {agent.session_id} | {agent.status}]", file=sys.stderr)
        print(f">>> {prompt}\n", file=sys.stderr)

        # attach: send the prompt and consume typed events as they stream in.
        stream = agent.run_streamed(prompt)
        for event in stream:
            if event.type == AgentEventType.TOKEN:
                print(event.text, end="", flush=True)  # live reply -> stdout
            elif event.type == AgentEventType.TOOL_CALL:
                print(f"\n[tool] {event.tool_name}", file=sys.stderr)
            elif event.type == AgentEventType.HITL_REQUESTED:
                print(f"\n[hitl auto-approved] {event.request_id}", file=sys.stderr)

        result = stream.result
        print(
            f"\n\n[{result.status}] "
            f"tokens in={result.usage.get('tokens_in')} "
            f"out={result.usage.get('tokens_out')} "
            f"| captured {len(result.final_output)} chars",
            file=sys.stderr,
        )

    # session is destroyed here.
    return 0 if stream.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
