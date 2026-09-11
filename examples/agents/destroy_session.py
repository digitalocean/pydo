"""Destroy a session. Set DIGITALOCEAN_TOKEN and SESSION_ID."""

import os

from pydo import Client

SESSION_ID = os.environ["SESSION_ID"]

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
client.agents.sessions.destroy(SESSION_ID)

print("ok", SESSION_ID)
