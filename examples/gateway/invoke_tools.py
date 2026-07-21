"""Invoke Action Gateway tools in parallel (action_invoke).

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
  END_USER_ID
"""

import os

from pydo.action_gateway import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
session = client.sessions.create(
    end_user_id=os.environ.get("END_USER_ID", "example-user"),
)

envelope = session.tools.invoke(
    [
        {
            "tool": "web_search",
            "arguments": {"query": "DigitalOcean Gradient", "max_results": 3},
        },
        {"tool": "web_fetch", "arguments": {"url": "https://www.digitalocean.com"}},
    ],
    rationale="demonstrate parallel tool invocation",
)

print(f"{envelope.success_count}/{envelope.total_count} succeeded\n")
for item in envelope.results:
    result = item.result
    print(f"[{item.index}] {item.tool}: {result.status}")
    if result.status == "succeeded":
        print(f"    output: {str(result.get('output'))[:200]}")
    else:
        error = result.get("error", {})
        print(f"    error ({error.get('class')}): {error.get('message')}")

output = session.tools.invoke_one(
    "web_search", {"query": "MCP protocol", "max_results": 1}
)
print("\ninvoke_one output:", str(output)[:200])
