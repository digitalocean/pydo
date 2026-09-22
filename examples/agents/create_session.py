"""Create a session from an agent manifest (``agents.yaml``).

A session is created entirely from the agent spec — the runtime adapter,
sandbox template, env vars, etc. are all defined in the manifest. The client
uploads it verbatim (``Content-Type: application/x-yaml``); the server parses
and validates it.

Required env:
  DIGITALOCEAN_TOKEN
  PYDO_AGENTS_ENDPOINT  (stage2: https://api.s2r1.internal.digitalocean.com)
  AGENT_SPEC            path to the agent spec YAML (default: agent-spec.yaml)
"""

import json
import os

from pydo import Client

spec_path = os.environ.get("AGENT_SPEC", "agent-spec.yaml")
with open(spec_path, "r", encoding="utf-8") as fh:
    manifest = fh.read()

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
resp = client.agents.sessions.create_from_manifest(manifest)

print(json.dumps(resp, indent=2, default=str))
