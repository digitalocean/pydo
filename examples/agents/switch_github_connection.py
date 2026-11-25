"""Switch a running session's GitHub connection. Set DIGITALOCEAN_TOKEN,
SESSION_ID, CONNECTION (the new connection's ``user_id``) and KEEP_SECRETS.

The session's ``GITHUB_TOKEN`` secret must have been created with ``actor``
(``{source: oauth, provider: github, actor: <user_id>}``). The new connection
must be active and owned by you; another team member's connection is refused.
``secrets`` is a full set: a secret left out is removed. List every other
secret the session has in KEEP_SECRETS (comma-separated names); each is sent as
``{}`` to keep it. The agent restarts to read the new token. See ``SessionsOperations.update_config``
for the full rules.
"""

import os

from pydo import Client
from pydo.agents import (
    AgentSession,
    SessionConfigUpdateError,
    SessionConfigUpdateOutcome,
)

SESSION_ID = os.environ["SESSION_ID"]
CONNECTION = os.environ["CONNECTION"]
KEEP_SECRETS = [n.strip() for n in os.environ["KEEP_SECRETS"].split(",") if n.strip()]

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
sessions = client.agents.sessions

active = [
    c["user_id"]
    for c in sessions.list_connections("github", status="active").get("connections", [])
]
if CONNECTION not in active:
    raise SystemExit(f"no active GitHub connection {CONNECTION!r}; active: {active}")

MANIFEST = (
    "secrets:\n"
    "  GITHUB_TOKEN:\n"
    "    source: oauth\n"
    "    provider: github\n"
    f"    actor: {CONNECTION}\n"
    + "".join(f"  {name}: {{}}\n" for name in KEEP_SECRETS)
)

resp = sessions.update_config(SESSION_ID, manifest_yaml=MANIFEST)
print("outcome:", resp.outcome, "warnings:", resp.get("warnings", []))

if resp.outcome == SessionConfigUpdateOutcome.ACCEPTED:
    try:
        update = AgentSession(sessions, SESSION_ID).wait_until_updated()
        print("update:", update.get("state"))
    except SessionConfigUpdateError as exc:
        print("failed:", exc, "reverted:", exc.reverted)
