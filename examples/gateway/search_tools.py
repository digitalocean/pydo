"""Search the Action Gateway tool catalog by use case (action.search).

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
  USE_CASE
"""

import os

from pydo import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])

use_case = os.environ.get("USE_CASE", "search the public web for a topic")

payload = client.gateway.tools.search(use_case, limit=3)

for group in payload.get("results", []):
    print(f"use case: {group.get('use_case')}")
    for match in group.get("results", []):
        print(f"  {match.get('name')} (score {match.get('score')})")
        print(f"    {match.get('description', '')[:100]}")
    if group.get("guidance"):
        print(f"  guidance: {group['guidance']}")
