"""Change a running session's tools. Set DIGITALOCEAN_TOKEN and SESSION_ID.

The manifest holds only the sections to change. ``tools`` is the full
replacement list; ``env`` and ``secrets`` (when sent) are full sets.
"""

import os

from pydo import Client
from pydo.agents import AgentSession, SessionConfigUpdateError, SessionConfigUpdateOutcome

SESSION_ID = os.environ["SESSION_ID"]
MANIFEST = """\
tools:
  - do.actions:
      tools: [toolbelt:read-only@1]
"""

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
sessions = client.agents.sessions

resp = sessions.update_config(SESSION_ID, manifest_yaml=MANIFEST)
print("outcome:", resp.outcome, "warnings:", resp.get("warnings", []))

if resp.outcome == SessionConfigUpdateOutcome.ACCEPTED:
    try:
        update = AgentSession(sessions, SESSION_ID).wait_until_updated()
        print("update:", update.get("state"))
    except SessionConfigUpdateError as exc:
        print("failed:", exc, "reverted:", exc.reverted)
