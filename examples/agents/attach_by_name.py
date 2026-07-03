"""Look up a hosted-agent session by name (instead of by id).

Sessions can be filtered server-side by name (``GET /v2/agents/sessions?name=``).
This script lists the matches and resolves the name to a session handle via
``client.agents.attach_by_name(...)``.

Required env:
  DIGITALOCEAN_TOKEN
  PYDO_AGENTS_ENDPOINT   stage2: https://api.s2r1.internal.digitalocean.com
  SESSION_NAME           the session name to look up
"""

import os
import sys

from pydo import Client


def main() -> int:
    name = os.environ["SESSION_NAME"]

    client = Client(
        token=os.environ["DIGITALOCEAN_TOKEN"],
        agents_endpoint=os.environ.get("PYDO_AGENTS_ENDPOINT"),
    )

    resp = client.agents.sessions.list(name=name)
    sessions = resp.get("sessions", []) if hasattr(resp, "get") else []
    print(f"[list name={name!r}] {len(sessions)} match(es):", file=sys.stderr)
    for s in sessions:
        print(f"  {s['session_id']}  {s['name']}  {s['status']}", file=sys.stderr)

    if not sessions:
        # Help diagnose a 0-match result: show what names actually exist now.
        all_resp = client.agents.sessions.list()
        all_sessions = all_resp.get("sessions", []) if hasattr(all_resp, "get") else []
        print(
            f"[attach_by_name] no session named {name!r}. "
            f"{len(all_sessions)} session(s) currently exist:",
            file=sys.stderr,
        )
        for s in all_sessions:
            print(f"  {s['name']}  ({s['status']})", file=sys.stderr)
        return 1

    agent = client.agents.attach_by_name(name)
    print(f"[attach_by_name] resolved session_id: {agent.session_id}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
