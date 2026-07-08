"""Attach to an EXISTING agent session and stream one turn.

Like ``doctl agents attach``: connect to a session that already exists, send a
prompt, and consume the SSE event feed through the high-level API — no thread,
no raw event-string matching. attach() never destroys the session, so it stays
alive for further turns.

Get a SESSION_ID first by creating one (the session stays up):
    AGENT_SPEC=... python examples/agents/create_session.py
then copy the "session_id" it prints.

Required env:
  DIGITALOCEAN_TOKEN
  PYDO_AGENTS_ENDPOINT   stage2: https://api.s2r1.internal.digitalocean.com
  SESSION_ID             the session to attach to

Optional env:
  PROMPT                 message to send (default below)
"""

import os
import sys

from pydo import Client
from pydo.agents import AgentEventType

client = Client(
    token=os.environ["DIGITALOCEAN_TOKEN"],
    agents_endpoint=os.environ.get("PYDO_AGENTS_ENDPOINT"),
)

agent = client.agents.attach(os.environ["SESSION_ID"])
prompt = os.environ.get("PROMPT", "In one short sentence, what is DigitalOcean?")

print(f"[attached {agent.session_id}]\n>>> {prompt}\n", file=sys.stderr)

stream = agent.run_streamed(prompt)  # opens the stream, sends input, yields events
for event in stream:
    if event.type == AgentEventType.TOKEN:
        print(event.text, end="", flush=True)  # live reply -> stdout
    elif event.type == AgentEventType.TOOL_CALL:
        print(f"\n[tool] {event.tool_name}", file=sys.stderr)
    elif event.type == AgentEventType.HITL_REQUESTED:
        print(f"\n[hitl auto-approved] {event.request_id}", file=sys.stderr)

result = stream.result
print(
    f"\n\n[{result.status}] captured {len(result.final_output)} chars "
    f"(tokens out={result.usage.get('tokens_out')})",
    file=sys.stderr,
)
# attach() leaves the session running; destroy it when done:
#   SESSION_ID=... python examples/agents/destroy_session.py
