"""Request and approve a tool invocation in one session.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  ACTOR_ID
  TOOL_NAME     default: exa_web_search
"""

import os

from pydo.action_gateway import ActionGatewayClient


def find_approval_id(value):
    """Find an approval ID in a gateway result envelope."""
    if isinstance(value, dict):
        for key in ("approval_id", "approvalId"):
            if value.get(key):
                return value[key]
        for nested in value.values():
            approval_id = find_approval_id(nested)
            if approval_id:
                return approval_id
    elif isinstance(value, list):
        for nested in value:
            approval_id = find_approval_id(nested)
            if approval_id:
                return approval_id
    return None


client = ActionGatewayClient(token=os.environ["DIGITALOCEAN_TOKEN"])
session = client.session.create(
    actor_id=os.environ.get("ACTOR_ID", "example-user"),
    permissions={"default_action": "ask"},
)

tool_name = os.environ.get("TOOL_NAME", "exa_web_search")
arguments = {"query": "DigitalOcean", "max_results": 3}
result = session.tools.invoke(
    [{"tool": tool_name, "arguments": arguments}],
    rationale="demonstrate SDK approval flow",
)

approval_id = find_approval_id(result)
if not approval_id:
    raise RuntimeError(f"invocation did not request approval: {result!r}")

input(f"Approve {approval_id}? Press Enter to continue...")
session.approve(approval_id)

result = session.tools.invoke(
    [{"tool": tool_name, "arguments": arguments}],
    rationale="retry after approval",
)
print(result)
