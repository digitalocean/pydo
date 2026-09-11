"""Send input to a session. Set DIGITALOCEAN_TOKEN and SESSION_ID."""

import json
import os

from pydo import Client

SESSION_ID = os.environ["SESSION_ID"]
TEXT = "Summarise the README in two sentences."

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
resp = client.agents.sessions.send_input(SESSION_ID, text=TEXT)

print(json.dumps(resp, indent=2, default=str))
