"""Pause and resume a hosted-agent session.

Attaches to an existing session (by id or by name), pauses it, waits for it to
report ``SESSION_STATUS_PAUSED``, then resumes it and waits for ``READY``.

Required env:
  DIGITALOCEAN_TOKEN
  PYDO_AGENTS_ENDPOINT   stage2: https://api.s2r1.internal.digitalocean.com

Pick a session with one of (SESSION_ID takes precedence):
  SESSION_ID             the session id to pause/resume
  SESSION_NAME           resolve the session by name instead
"""

import os
import sys
import time

from pydo import Client
from pydo.agents.custom_models import SessionStatus


def _wait_for_status(agent, target, *, timeout=120.0, poll_interval=2.0):
    """Poll until the session reaches ``target`` (or a terminal/failed state)."""
    deadline = time.monotonic() + timeout
    while True:
        agent.refresh()
        status = agent.status
        print(f"  status: {status}", file=sys.stderr)
        if status == target:
            return
        if status in (SessionStatus.FAILED, SessionStatus.DESTROYED):
            raise RuntimeError(f"session {agent.session_id} is {status}")
        if time.monotonic() > deadline:
            raise TimeoutError(
                f"session {agent.session_id} did not reach {target} in {timeout}s "
                f"(last status: {status})"
            )
        time.sleep(poll_interval)


def main() -> int:
    client = Client(
        token=os.environ["DIGITALOCEAN_TOKEN"],
        agents_endpoint=os.environ.get("PYDO_AGENTS_ENDPOINT"),
    )

    session_id = os.environ.get("SESSION_ID")
    session_name = os.environ.get("SESSION_NAME")
    if session_id:
        agent = client.agents.attach(session_id)
    elif session_name:
        agent = client.agents.attach_by_name(session_name)
    else:
        print("set SESSION_ID or SESSION_NAME", file=sys.stderr)
        return 2

    print(f"[attach] session_id={agent.session_id}", file=sys.stderr)
    agent.refresh()
    print(f"[attach] current status: {agent.status}", file=sys.stderr)

    print("[pause] pausing session...", file=sys.stderr)
    agent.pause()
    _wait_for_status(agent, SessionStatus.PAUSED)
    print("[pause] session is PAUSED", file=sys.stderr)

    print("[resume] resuming session...", file=sys.stderr)
    agent.resume()
    _wait_for_status(agent, SessionStatus.READY)
    print("[resume] session is READY", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
