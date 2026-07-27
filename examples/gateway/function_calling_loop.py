"""Agentic function-calling loop: chat completions + Action Gateway session.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
  ACTOR_ID
  MODEL
  PROMPT
"""

import json
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
    tool_names = {}
    for tool_call in message["tool_calls"]:
        function = tool_call["function"]
        tool_names[tool_call["id"]] = function["name"]
        print(f"\n[tool call: {function['name']} id={tool_call['id']}]")
        try:
            arguments = json.loads(function["arguments"])
            print(json.dumps(arguments, indent=2))
        except (TypeError, ValueError):
            print(function["arguments"])

    tool_messages = session.handle_tool_calls(response)
    if any(name != "action_search" for name in tool_names.values()):
        tool_choice = "auto"
    for tool_message in tool_messages:
        tool_call_id = tool_message.get("tool_call_id", "unknown")
        tool_name = tool_names.get(tool_call_id, "unknown")
        print(f"[tool result: {tool_name} id={tool_call_id}]")
        try:
            result = json.loads(tool_message["content"])
            print(json.dumps(result, indent=2))
        except (TypeError, ValueError):
            print(tool_message["content"])
    messages.extend(tool_messages)

print("\nFinal answer:\n")
print(message.get("content"))
