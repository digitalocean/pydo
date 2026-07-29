"""Use the OpenAPI-generated Action Gateway control-plane APIs.

Required env:
  DIGITALOCEAN_TOKEN
"""

import os

from pydo.action_gateway import ActionGatewayClient

client = ActionGatewayClient(token=os.environ["DIGITALOCEAN_TOKEN"])

print(client.tools.list())
print(client.tools.list_toolkits())
print(client.tools.list_providers())
print(client.tools.get_definition("exa_web_search", version="v1"))

print(client.connections.list(user_id="example-user"))
print(client.users.list())
print(client.sessions_api.list(end_user_id="example-user"))
