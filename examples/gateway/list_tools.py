"""List Action Gateway tools for a session.

By default the session exposes three meta-tools (action_search,
action_invoke, action_code). Pass include_all=True to include tools configured
through config.preloadTools.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
  ACTOR_ID
"""

import os

from pydo.action_gateway import ActionGatewayClient

client = ActionGatewayClient(token=os.environ["DIGITALOCEAN_TOKEN"])
session = client.session.create(
    actor_id=os.environ.get("ACTOR_ID", "example-user"),
)

print("MCP URL:", session.url)
print("\nMeta-tools (default):")
for tool in session.tools.list():
    print(f"  {tool.name}: {tool.get('description', '')[:80]}")

print("\nAll tools exposed by this session MCP endpoint:")
for tool in session.tools.list(include_all=True):
    print(f"  {tool.name}: {tool.get('description', '')[:80]}")
