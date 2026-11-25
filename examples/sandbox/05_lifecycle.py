"""Sandbox lifecycle: create, list, get, pause, resume, connect, get_info, delete.

    python examples/sandbox/05_lifecycle.py

You should see the state at each step: running, paused, running again, and a
final line saying the sandbox is gone.

Needs DIGITALOCEAN_ACCESS_TOKEN. Set DIGITALOCEAN_API_URL to use another API address.
"""

from pydo import Sandbox
from pydo.sandbox import NotFoundError

with Sandbox.create() as sbx:
    sandbox_id = sbx.sandbox_id
    print("created   :", sandbox_id, sbx.state)

    # list() walks every page of your sandboxes.
    mine = [s for s in Sandbox.list() if s.sandbox_id == sandbox_id]
    print("in list   :", bool(mine))

    print("get       :", Sandbox.get(sandbox_id).state)

    print("paused    :", sbx.pause().state)
    print("is_running:", sbx.is_running())

    print("resumed   :", sbx.resume().state)

    # connect() fetches by id and resumes the sandbox if it is paused.
    other = Sandbox.connect(sandbox_id)
    print("connect   :", other.state)
    print("get_info  :", other.get_info())
    print("is_running:", other.is_running())
    other.close()  # closes the connection only; it does not delete

try:
    Sandbox.get(sandbox_id)
except NotFoundError:
    print("deleted   :", sandbox_id, "is gone")
