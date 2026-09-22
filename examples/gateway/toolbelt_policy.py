"""Create a session whose policy allows one pinned toolbelt.

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
    permissions={
        "default_action": "ask",
        "rules": [
            {"tool": "toolbelt:search-toolbelt@1", "action": "allow"},
            {"tool": "exa_web_search", "action": "allow"},
        ],
    },
)

print("MCP URL:", session.url)
print("tools:", [tool["function"]["name"] for tool in session.tools()])
