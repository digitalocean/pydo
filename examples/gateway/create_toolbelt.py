"""Create a versioned Action Gateway toolbelt.

Required env:
  DIGITALOCEAN_TOKEN
"""

import os

from pydo.action_gateway import ActionGatewayClient

client = ActionGatewayClient(token=os.environ["DIGITALOCEAN_TOKEN"])

toolbelt = client.create_toolbelt(
    name="search-toolbelt",
    tools=[
        "exa_web_search",
        "exa_web_fetch",
    ],
)

print(toolbelt.ref)

# Public Tool Registry APIs are generated from DigitalOcean's OpenAPI spec.
print(client.toolbelts.list(status="active"))
print(client.toolbelts.get("search-toolbelt", version="1"))
client.toolbelts.add_tools(
    "search-toolbelt",
    body={"tools": ["jira_create_issue"]},
)
client.toolbelts.delete_tools(
    "search-toolbelt",
    body={"tools": ["exa_web_fetch"]},
)

# Delete the toolbelt when it is no longer needed.
# client.toolbelts.delete("search-toolbelt")
