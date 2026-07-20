"""List Action Gateway tools for a session.

By default the session exposes three meta-tools (action_search,
action_invoke, action_code). Pass include_all=True for the concrete catalog.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
  END_USER_ID
"""

import os

from pydo.action_gateway import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
session = client.sessions.create(
    end_user_id=os.environ.get("END_USER_ID", "example-user"),
)

print("MCP URL:", session.url)
print("\nMeta-tools (default):")
for tool in session.tools.list():
    print(f"  {tool.name}: {tool.get('description', '')[:80]}")

print("\nFull concrete catalog:")
for tool in session.tools.list(include_all=True):
    print(f"  {tool.name}: {tool.get('description', '')[:80]}")
