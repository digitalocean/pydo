"""Use every OpenAPI-generated Action Gateway resource.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  ACTOR_ID
  CONNECTION_ID   enables get, update, and delete connection examples
  SESSION_URN     enables session deletion example
"""

import os

from pydo.action_gateway import ActionGatewayClient

client = ActionGatewayClient(token=os.environ["DIGITALOCEAN_TOKEN"])
actor_id = os.environ.get("ACTOR_ID", "example-user")

# Tools are read-only catalog resources.
print("Tools:", client.tools.list(toolkit_id="exa"))
print("Toolkits:", client.tools.list_toolkits())
print("Providers:", client.tools.list_providers())
print(
    "Definition:",
    client.tools.get_definition("exa_web_search", version="v1"),
)

# Toolbelts support create, list, get, membership changes, and delete.
toolbelt = client.toolbelts.create(
    body={"name": "search-toolbelt", "tools": ["exa_web_search"]}
)
print("Created toolbelt:", toolbelt)
print("Toolbelts:", client.toolbelts.list(status="active"))
print("Toolbelt:", client.toolbelts.get("search-toolbelt"))
client.toolbelts.add_tools(
    "search-toolbelt",
    body={"tools": ["exa_web_fetch"]},
)
client.toolbelts.delete_tools(
    "search-toolbelt",
    body={"tools": ["exa_web_fetch"]},
)

# Connections support create, list, get, parameter updates, and delete.
connection = client.connections.create(
    body={"provider": "github", "user_id": actor_id, "scopes": ["repo"]}
)
print("Created connection:", connection)
print("Connections:", client.connections.list(user_id=actor_id))

connection_id = os.environ.get("CONNECTION_ID")
if connection_id:
    print("Connection:", client.connections.get(connection_id))
    client.connections.update(
        connection_id,
        body={"connection_parameters": {"site_url": "https://github.com"}},
    )
    client.connections.delete(connection_id)

# Users are derived from their sessions and connections.
print("Users:", client.users.list())
print("User:", client.users.get(actor_id))

# Sessions are generated too. The convenience session API delegates creation
# to this same generated resource and returns a session bound to response.mcpUrl.
print("Sessions:", client.sessions_api.list(end_user_id=actor_id))
session = client.session.create(
    actor_id=actor_id,
    tools=["exa_web_search@v1"],
    config={"preloadTools": ["exa_web_search@v1"]},
    permissions={"default_action": "ask"},
)
print("Session MCP URL:", session.url)

session_urn = os.environ.get("SESSION_URN")
if session_urn:
    client.sessions_api.delete(session_urn)

# Uncomment when the example toolbelt is no longer needed.
# client.toolbelts.delete("search-toolbelt")
