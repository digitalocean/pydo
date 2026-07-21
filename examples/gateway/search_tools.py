"""Search the Action Gateway tool catalog by use case (action_search).

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
  END_USER_ID
  USE_CASE
"""

import os

from pydo.action_gateway import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
session = client.sessions.create(
    end_user_id=os.environ.get("END_USER_ID", "example-user"),
)

use_case = os.environ.get("USE_CASE", "search the public web for a topic")

payload = session.tools.search(use_case, limit=3)

for group in payload.get("results", []):
    print(f"use case: {group.get('use_case')}")
    for match in group.get("results", []):
        print(f"  {match.get('name')} (score {match.get('score')})")
        print(f"    {match.get('description', '')[:100]}")
    if group.get("guidance"):
        print(f"  guidance: {group['guidance']}")
