"""Agentic function-calling loop: chat completions + Action Gateway session.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
  ACTOR_ID
  MODEL
  PROMPT
"""

import os

from pydo.action_gateway import ActionGatewayClient

client = ActionGatewayClient(token=os.environ["DIGITALOCEAN_TOKEN"])
session = client.session.create(
    actor_id=os.environ.get("ACTOR_ID", "example-user"),
)

model = os.environ.get("MODEL", "openai-gpt-5.4")
prompt = os.environ.get("PROMPT", "Search the web for information on DigitalOcean.")

tools = session.tools()
messages = [{"role": "user", "content": prompt}]
tool_choice = "required"

while True:
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
    )
    message = response.choices[0].message
    if not message.get("tool_calls"):
        break

    messages.append(dict(message))
    tool_messages = session.handle_tool_calls(response)
    if any(
        tool_call["function"]["name"] != "action_search"
        for tool_call in message["tool_calls"]
    ):
        tool_choice = "auto"
    messages.extend(tool_messages)

print("\nFinal answer:\n")
print(message.get("content"))
