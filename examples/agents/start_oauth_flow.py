"""Start GitHub OAuth. Set DIGITALOCEAN_TOKEN and SESSION_ID."""

import json
import os

from pydo import Client
from pydo.agents import OAuthProvider

SESSION_ID = os.environ["SESSION_ID"]

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
resp = client.agents.sessions.start_oauth_flow(
    SESSION_ID,
    OAuthProvider.GITHUB,
    requested_scopes=["repo"],
)

print(json.dumps(resp, indent=2, default=str))
