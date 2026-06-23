"""Get a session. Set DIGITALOCEAN_TOKEN and SESSION_ID."""

import json
import os

from pydo import Client

SESSION_ID = os.environ["SESSION_ID"]

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
resp = client.agents.sessions.get(SESSION_ID)

print(json.dumps(resp, indent=2, default=str))
