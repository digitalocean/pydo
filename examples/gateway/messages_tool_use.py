"""Tool use via the Messages API (Anthropic format) + Action Gateway.

Identical loop to function_calling_loop.py — the only change is the
provider passed at construction, which switches the tools= format and
the tool-call parsing to the Messages API shapes.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
  MODEL
  PROMPT
"""

import os

from pydo import Client
from pydo.gateway import MessagesProvider

client = Client(
    token=os.environ["DIGITALOCEAN_TOKEN"],
    gateway_provider=MessagesProvider(),
)

model = os.environ.get("MODEL", "anthropic-claude-3.5-haiku")
prompt = os.environ.get(
    "PROMPT", "Find the latest news about DigitalOcean and summarize it."
)

tools = client.gateway.tools()  # Messages-format tool definitions

messages = [{"role": "user", "content": prompt}]

while True:
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        tools=tools,
        messages=messages,
    )
    if response.get("stop_reason") != "tool_use":
        break

    messages.append({"role": "assistant", "content": list(response.content)})
    # One user turn containing all tool_result blocks:
    messages.extend(client.gateway.handle_tool_calls(response))

for block in response.content:
    if block.get("type") == "text":
        print(block.text)
