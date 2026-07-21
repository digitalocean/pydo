"""Agentic function-calling loop: chat completions + Action Gateway session.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
  END_USER_ID
  MODEL
  PROMPT
"""

import os

from pydo.action_gateway import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
session = client.sessions.create(
    end_user_id=os.environ.get("END_USER_ID", "example-user"),
)

model = os.environ.get("MODEL", "openai-gpt-4o")
prompt = os.environ.get(
    "PROMPT", "Find the latest news about DigitalOcean and summarize it."
)

tools = session.tools()
messages = [{"role": "user", "content": prompt}]

while True:
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
    )
    message = response.choices[0].message
    if not message.get("tool_calls"):
        break

    messages.append(dict(message))
    tool_messages = session.handle_tool_calls(response)
    for tool_message in tool_messages:
        print(f"[tool result] {str(tool_message['content'])[:120]}")
    messages.extend(tool_messages)

print("\nFinal answer:\n")
print(message.get("content"))
