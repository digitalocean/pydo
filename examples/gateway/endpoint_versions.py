"""Publish, pin, promote, and delete Action Gateway endpoint versions.

Versions are immutable. Publishing one makes it the head that the endpoint's
MCP URL serves; promoting an older version copies it into a new head. A
version's own MCP URL keeps serving that version until it is deleted.

Required env:
  DIGITALOCEAN_TOKEN
  ENDPOINT_ID

Optional env:
  ACTOR_ID   must match the endpoint's actor
"""

import os

from pydo.action_gateway import ActionGatewayClient

client = ActionGatewayClient(token=os.environ["DIGITALOCEAN_TOKEN"])
endpoints = client.endpoints
endpoint_id = os.environ["ENDPOINT_ID"]
actor_id = os.environ.get("ACTOR_ID", "example-user")

previous = endpoints.get(endpoint_id).head_version

# Publish a version that also allows page fetches. It becomes the head.
latest = endpoints.create_version(
    endpoint_id,
    actor_id=actor_id,
    tools=["exa_web_search@v1", "exa_web_fetch@v1"],
    permissions={"default_action": "ask"},
)
print("Published", latest.id, "pinned at", latest.mcp_url)

# Agents on the endpoint URL now get the new version; the pinned URL does not
# change.
for version in endpoints.list_versions(endpoint_id).versions:
    print(version.version_number, version.mcp_url)

if previous is not None:
    print("Still pinned:", [t.name for t in previous.tools.list(include_all=True)])

    # Roll back by promoting the previous version into a new head.
    rolled_back = endpoints.promote(endpoint_id, previous.id)
    print(
        "Promoted",
        rolled_back.promoted_from_version_number,
        "to",
        rolled_back.version_number,
    )

    # Delete the version published above; its pinned URL stops working.
    endpoints.delete_version(latest.id)

# Rename the endpoint or change its Insights consent for every version.
endpoints.update(endpoint_id, insights={"logs": True})
