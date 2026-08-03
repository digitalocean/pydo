"""Create an Action Gateway session and print its MCP URL.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  ACTOR_ID
"""

import os

from pydo.action_gateway import ActionGatewayClient

client = ActionGatewayClient(token=os.environ["DIGITALOCEAN_TOKEN"])
session = client.session.create(
    actor_id=os.environ.get("ACTOR_ID", "example-user"),
    tools=["exa_web_search@v1"],
    config={"preloadTools": ["exa_web_search@v1"]},
    permissions={
        "default_action": "ask",
        "rules": [{"tool": "exa_web_search", "action": "allow"}],
    },
)

print(session.url)
