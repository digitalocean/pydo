"""Stream session events.

Required env:
  DIGITALOCEAN_TOKEN
  SESSION_ID
  PYDO_AGENTS_ENDPOINT  (stage2: https://api.s2r1.internal.digitalocean.com)

Tip: open this stream *before* send_input.py so you catch live events.
If the run already finished, the stream may sit idle until the next input.
"""

import os
import sys

from pydo import Client

SESSION_ID = os.environ["SESSION_ID"]

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
print(f"agents endpoint: {client.agents.base_url}", file=sys.stderr)

with client.agents.sessions.stream(SESSION_ID) as events:
    for event in events:
        # SPI wire (harness-api HTTP handler): type + data.text
        if getattr(event, "type", None) == "run.token_delta" and event.get("data"):
            print(event.data.text, end="", flush=True)
        # grpc-gateway proto envelope (legacy)
        elif "token_chunk" in event:
            print(event.token_chunk.text, end="", flush=True)
        else:
            print(event)
