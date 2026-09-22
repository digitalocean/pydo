"""One-liner blocking run: create from spec -> run -> print -> destroy.

The high-level API collapses the whole flow into ``agent.run(prompt)``, which
blocks until the run finishes and returns the assembled output. The ``with``
block auto-destroys the session on exit.

Required env:
  DIGITALOCEAN_TOKEN
  PYDO_AGENTS_ENDPOINT   stage2: https://api.s2r1.internal.digitalocean.com
  AGENT_SPEC             path to the agent spec YAML

Optional env:
  PROMPT
"""

import os

from pydo import Client

client = Client(
    token=os.environ["DIGITALOCEAN_TOKEN"],
    agents_endpoint=os.environ.get("PYDO_AGENTS_ENDPOINT"),
)

with open(os.environ.get("AGENT_SPEC", "agent-spec.yaml"), encoding="utf-8") as fh:
    manifest = fh.read()

prompt = os.environ.get("PROMPT", "In one short sentence, what is DigitalOcean?")

with client.agents.start(manifest) as agent:  # auto-destroys on exit
    print(agent.run(prompt).final_output)
