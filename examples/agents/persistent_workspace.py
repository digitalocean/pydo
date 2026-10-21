"""Keep files across sessions with a persistent workspace.

Flow:
  1. Create a workspace (with an Idempotency-Key so a retry cannot create a second one).
  2. Create a session from an Agent Config with the workspace attached.
  3. Destroy the session.
  4. Poll the workspace until it is AVAILABLE again.
  5. Create a second session on the same workspace.
  6. Clean up: destroy the session, wait for the workspace, delete it.

Required env:
  DIGITALOCEAN_TOKEN
  CONFIG_ID              id of an existing Agent Config (see test_agent_configs.py)

Optional env:
  PYDO_AGENTS_ENDPOINT   default: https://api.digitalocean.com

A 501 from the API means workspaces are not enabled for the team. Attaching a
workspace that is not AVAILABLE (for example one that is still releasing)
returns 409.
"""

import os
import time
import uuid

from pydo import Client
from pydo.agents import WorkspaceState


def wait_for_state(client, workspace_id, target, *, timeout=300.0, poll_interval=3.0):
    """Poll until the workspace reaches ``target`` (or fails / times out)."""
    deadline = time.monotonic() + timeout
    while True:
        state = client.agents.workspaces.get(workspace_id).workspace.state
        print(f"  workspace {workspace_id}: {state}")
        if state == target:
            return
        if state == WorkspaceState.FAILED:
            raise RuntimeError(f"workspace {workspace_id} is {state}")
        if time.monotonic() > deadline:
            raise TimeoutError(
                f"workspace {workspace_id} did not reach {target} in {timeout}s "
                f"(last state: {state})"
            )
        time.sleep(poll_interval)


client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
config_id = os.environ["CONFIG_ID"]

workspace = client.agents.workspaces.create(
    10,
    name="pydo-example",
    idempotency_key=str(uuid.uuid4()),
).workspace
print("created workspace", workspace.workspace_id, workspace.state)

# The workspaces a new session can attach are the AVAILABLE ones. A page can be
# shorter than page_size, even empty, while next_page_token is not empty, so
# keep requesting pages until it is empty.
page_token = None
while True:
    page = client.agents.workspaces.list(
        state=WorkspaceState.AVAILABLE, page_token=page_token
    )
    for available in page.workspaces:
        print("available workspace:", available.workspace_id, available.name)
    page_token = page.next_page_token
    if not page_token:
        break

try:
    for run in (1, 2):
        session = client.agents.sessions.create_from_config(
            name=f"pydo-workspace-example-{run}",
            config_id=config_id,
            workspace_id=workspace.workspace_id,
        ).session
        print(f"session {run}:", session.session_id, "workspace:", session.workspace_id)

        # ... run the agent here; files it writes to the workspace persist ...

        client.agents.sessions.destroy(session.session_id)
        # The workspace is released asynchronously; it can only be attached
        # again (or deleted) once it is AVAILABLE.
        wait_for_state(client, workspace.workspace_id, WorkspaceState.AVAILABLE)
finally:
    client.agents.workspaces.delete(workspace.workspace_id)
    print("deleted workspace", workspace.workspace_id)
