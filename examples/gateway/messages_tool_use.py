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


def _assistant_content(response) -> list:
    """Return assistant content blocks, tolerating missing keys."""
    content = response.get("content")
    return list(content) if content else []


def _print_final_message(response) -> None:
    """Print assistant text from a Messages API response."""
    if response.get("type") == "error":
        error = response.get("error") or {}
        raise RuntimeError(f"Messages API error: {error}")

    blocks = _assistant_content(response)
    printed = False
    for block in blocks:
        if block.get("type") == "text" and block.get("text"):
            print(block["text"])
            printed = True

    if not printed:
        stop_reason = response.get("stop_reason")
        if stop_reason:
            print(f"(no text blocks; stop_reason={stop_reason!r})")
        print(response)


client = Client(
    token=os.environ["DIGITALOCEAN_TOKEN"],
    gateway_provider=MessagesProvider(),
)

model = os.environ.get("MODEL", "claude-opus-4-6")
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

    messages.append({"role": "assistant", "content": _assistant_content(response)})
    # One user turn containing all tool_result blocks:
    messages.extend(client.gateway.handle_tool_calls(response))

_print_final_message(response)
