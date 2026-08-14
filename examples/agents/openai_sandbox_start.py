"""Start an OpenAI Agents API sandbox-provider session on DigitalOcean.

Mirrors doctl ``agents start`` for ``openai-agent-codex`` manifests:

1. Create the OpenAI session from ``spec.openai`` (``$OPENAI_API_KEY``).
2. Resolve ``${ENV_ID}`` / ``${OPENAI_API_KEY}`` into ``spec.env``.
3. Create the DO sandbox session with ``openai_session_id``.
4. ``agent.run(...)`` bridges to OpenAI (not DO's SSE stream).

Required env:
  DIGITALOCEAN_TOKEN
  OPENAI_API_KEY
  PYDO_AGENTS_ENDPOINT  (optional; default api.digitalocean.com)
  AGENT_SPEC            path to agents.yaml (default: openai-agents.yaml)
"""

import os
import sys

from pydo import Client

SPEC_PATH = os.environ.get("AGENT_SPEC", "openai-agents.yaml")

DEFAULT_MANIFEST = """\
apiVersion: agents.digitalocean.com/v1alpha1
kind: Agent
metadata:
  name: openai-codex-session
spec:
  runtime:
    adapter: openai-agent-codex
  sandbox:
    idleTimeoutSeconds: 2700
  env:
    CODEX_ENVIRONMENT_ID: ${ENV_ID}
    CODEX_API_KEY: ${OPENAI_API_KEY}
  secrets:
    - name: CODEX_API_KEY
      source: tenantSecret
  openai:
    agent:
      model: gpt-5.6-sol
      instructions: "Answer the user clearly and concisely."
    environment:
      type: self_hosted
      workspace_directory: /workspace
    input:
      - role: user
        content:
          - type: input_text
            text: "What can you help with?"
"""


def main() -> int:
    if os.path.exists(SPEC_PATH):
        with open(SPEC_PATH, "r", encoding="utf-8") as fh:
            manifest = fh.read()
    else:
        print(
            f"[warn] {SPEC_PATH} not found; using embedded example manifest",
            file=sys.stderr,
        )
        manifest = DEFAULT_MANIFEST

    client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
    with client.agents.start(manifest) as agent:
        agent.wait_until_ready()
        print(
            f"do={agent.session_id} openai={agent.openai_session_id} "
            f"env={agent.openai_environment_id} kind={agent.agent_kind}",
            file=sys.stderr,
        )
        result = agent.run("List files in /workspace")
        print(result.final_output)
        return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
