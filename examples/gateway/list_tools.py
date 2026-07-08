"""List Action Gateway tools.

By default the gateway exposes three meta-tools (action.search,
action.invoke, action.code) that let a model drive tool discovery and
execution itself. Pass include_all=True for the full concrete catalog.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
"""

import os

from pydo import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])

print("Meta-tools (default):")
for tool in client.gateway.tools.list():
    print(f"  {tool.name}: {tool.get('description', '')[:80]}")

print("\nFull concrete catalog:")
for tool in client.gateway.tools.list(include_all=True):
    print(f"  {tool.name}: {tool.get('description', '')[:80]}")
