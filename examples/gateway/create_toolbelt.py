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
