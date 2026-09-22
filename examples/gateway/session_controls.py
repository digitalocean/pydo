"""Control Action Gateway discovery, direct tools, and invocation policy.

The three session controls have separate roles:
  tools                         catalog available to action_search/action_invoke
  config.preloadTools           concrete tools also exposed directly over MCP
  permissions                   allow, ask, or deny each invocation

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
    tools=["exa_web_search@v1", "exa_web_fetch@v1"],
    config={"preloadTools": ["exa_web_search@v1"]},
    permissions={
        "default_action": "deny",
        "rules": [
            {"tool": "exa_web_search", "action": "allow"},
            {"tool": "exa_web_fetch", "action": "ask"},
        ],
    },
)

print("MCP URL:", session.url)
print("Selected for search/invoke:", session.selected_tools)
print(
    "Exposed directly:",
    [tool.name for tool in session.tools.list(include_all=True)],
)

results = session.tools.search("search or fetch a public web page")
print("Search results:", results)
