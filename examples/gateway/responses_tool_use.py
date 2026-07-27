"""Tool use via the Responses API + Action Gateway session.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  ACTOR_ID
  MODEL
  PROMPT
"""

import os

from pydo.action_gateway import ActionGatewayClient, ResponsesProvider

client = ActionGatewayClient(
    token=os.environ["DIGITALOCEAN_TOKEN"],
    gateway_provider=ResponsesProvider(),
)
session = client.session.create(
    actor_id=os.environ.get("ACTOR_ID", "example-user"),
)

response = client.responses.create(
    model=os.environ.get("MODEL", "openai-gpt-4o"),
    input=os.environ.get(
        "PROMPT",
        "What DigitalOcean Droplet sizes are available in NYC3?",
    ),
    tools=session.tools(),
)

for tool_output in session.handle_tool_calls(response):
    print(tool_output)
