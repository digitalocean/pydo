"""Agentic function-calling loop: chat completions + Action Gateway.

The model is handed the gateway's meta-tools (action.search /
action.invoke / action.code) so it can discover and execute tools
itself. handle_tool_calls() runs whatever the model asked for and
returns ready-to-append tool messages; the loop continues until the
model answers with plain text.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
  MODEL
  PROMPT
"""

import os

from pydo import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])

model = os.environ.get("MODEL", "llama3.3-70b-instruct")
prompt = os.environ.get(
    "PROMPT", "Find the latest news about DigitalOcean and summarize it."
)

# Meta-tools by default; use tools(include_all=True) for the concrete catalog.
tools = client.gateway.tools()

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
    tool_messages = client.gateway.handle_tool_calls(response)
    for tool_message in tool_messages:
        print(f"[tool result] {str(tool_message['content'])[:120]}")
    messages.extend(tool_messages)

print("\nFinal answer:\n")
print(message.get("content"))
