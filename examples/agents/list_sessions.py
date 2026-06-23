"""List sessions. Set DIGITALOCEAN_TOKEN (and PYDO_AGENTS_ENDPOINT for stage2)."""

import os

from pydo import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])

resp = client.agents.sessions.list(page_size=50)
for session in resp.get("sessions", []):
    print(session.session_id, session.status, session.agent_kind)
