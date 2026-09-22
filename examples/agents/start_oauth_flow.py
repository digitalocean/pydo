"""Connect an external provider (GitHub) for your team. Set DIGITALOCEAN_TOKEN.

The connection is team-scoped: connecting once lets every hosted agent session
on the team perform authenticated git operations. The token is never returned
here; it is exchanged server-side at session time.
"""

import json
import os
import time

from pydo import Client
from pydo.agents import OAuthProvider

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])

start = client.agents.sessions.start_provider_auth(OAuthProvider.GITHUB)
print(json.dumps(start, indent=2, default=str))

if start.get("status") == "success":
    print("github is already connected for your team")
else:
    print(f"\nOpen this URL and authorize access:\n\n  {start.get('connect_url')}\n")
    if start.get("verification_code"):
        print(f"Verify the page shows code: {start.get('verification_code')}\n")
    print("Waiting for authorization to complete...")
    while True:
        poll = client.agents.sessions.poll_provider_auth(
            OAuthProvider.GITHUB, start.get("poll_url")
        )
        if poll.get("status") == "success":
            print("github connected successfully")
            break
        time.sleep(2)
