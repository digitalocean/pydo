"""Create a session.

Set DIGITALOCEAN_TOKEN (and PYDO_AGENTS_ENDPOINT for stage2).

Optional PYDO_AGENT_KIND (Private Beta server support):
  CLAUDE_CODE  → coding-claude-code  (default)
  OPENCODE     → coding-opencode
  CODEX_CLI    → coding-codex
  NONE         → coding-base (requires ops to enable AGENT_KIND_NONE on the server)
"""

import json
import os

from pydo import Client
from pydo.agents import AgentKind

_AGENT_KINDS = {
    "CLAUDE_CODE": AgentKind.CLAUDE_CODE,
    "OPENCODE": AgentKind.OPENCODE,
    "CODEX_CLI": AgentKind.CODEX_CLI,
    "NONE": AgentKind.NONE,
}

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])

kind_name = os.environ.get("PYDO_AGENT_KIND", "CLAUDE_CODE").upper()
try:
    agent_kind = _AGENT_KINDS[kind_name]
except KeyError as exc:
    raise SystemExit(
        f"Unknown PYDO_AGENT_KIND={kind_name!r}; "
        f"use one of: {', '.join(_AGENT_KINDS)}"
    ) from exc

resp = client.agents.sessions.create(
    agent_kind=agent_kind,
    repo_hint="digitalocean/pydo",
)

print(json.dumps(resp, indent=2, default=str))
