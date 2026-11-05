"""Create an Action Gateway endpoint and print its MCP URLs.

The endpoint URL always serves the endpoint's newest live version, so agents
keep their URL when you publish a new version. The version URL stays pinned to
the version that was just created.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  ACTOR_ID
  ENDPOINT_NAME
"""

import os

from pydo.action_gateway import ActionGatewayClient

client = ActionGatewayClient(token=os.environ["DIGITALOCEAN_TOKEN"])
endpoint = client.endpoints.create(
    os.environ.get("ENDPOINT_NAME", "pydo-example"),
    actor_id=os.environ.get("ACTOR_ID", "example-user"),
    tools=["exa_web_search@v1"],
    config={"preloadTools": ["exa_web_search@v1"]},
    permissions={
        "default_action": "ask",
        "rules": [{"tool": "exa_web_search", "action": "allow"}],
    },
)

print("Endpoint:", endpoint.id)
print("MCP URL (follows the newest version):", endpoint.mcp_url)
print("Version:", endpoint.head_version.id)
print("Version MCP URL (pinned):", endpoint.version_mcp_url)
