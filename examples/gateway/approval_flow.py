"""Approve Chat Completions tool calls through an Action Gateway session.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  ACTOR_ID
  MODEL
  PROMPT
"""

import json
import os

from pydo.action_gateway import ActionGatewayClient


def find_approval_ids(value):
    """Find approval IDs in gateway tool-result messages."""
    approval_ids = []
    if isinstance(value, dict):
        for key in ("approval_id", "approvalId"):
            if value.get(key):
                approval_ids.append(value[key])
        for nested in value.values():
            approval_ids.extend(find_approval_ids(nested))
    elif isinstance(value, list):
        for nested in value:
            approval_ids.extend(find_approval_ids(nested))
    elif isinstance(value, str):
        try:
            approval_ids.extend(find_approval_ids(json.loads(value)))
        except json.JSONDecodeError:
            pass
    return approval_ids


client = ActionGatewayClient(token=os.environ["DIGITALOCEAN_TOKEN"], timeout=30)
print("Creating Action Gateway session...")
session = client.session.create(
    actor_id=os.environ.get("ACTOR_ID", "example-user"),
    permissions={
        "default_action": "ask",
        "rules": [{"tool": "action_search", "action": "allow"}],
    },
)

model = os.environ.get("MODEL", "openai-gpt-4o")
messages = [
    {
        "role": "user",
        "content": os.environ.get(
            "PROMPT",
            "Search for the latest DigitalOcean news and summarize it.",
        ),
    }
]
tools = session.tools()
tool_choice = "required"

while True:
    print(f"Requesting next tool call from {model}...")
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
        parallel_tool_calls=False,
    )
    message = response.choices[0].message
    if not message.get("tool_calls"):
        break

    print("Executing requested gateway tool...")
    tool_messages = session.handle_tool_calls(response)
    approval_ids = list(dict.fromkeys(find_approval_ids(tool_messages)))
    for approval_id in approval_ids:
        input(f"Approve {approval_id}? Press Enter to continue...")
        session.approve(approval_id)

    if approval_ids:
        print("Retrying approved gateway tool...")
        tool_messages = session.handle_tool_calls(response)

    messages.append(dict(message))
    messages.extend(tool_messages)
    if any(
        tool_call["function"]["name"] != "action_search"
        for tool_call in message["tool_calls"]
    ):
        tool_choice = "auto"

print("\nFinal answer:\n")
print(message.get("content"))
