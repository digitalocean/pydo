"""Snapshot a sandbox, wait for it, fetch it, delete it.

    python examples/sandbox/07_snapshots.py

You should see the snapshot go from creating to complete, a get by id, a note
that listing snapshots is not available yet on the test API, and its deletion.

Needs DIGITALOCEAN_ACCESS_TOKEN. Set DIGITALOCEAN_API_URL to use another API address.
"""

import time

from pydo import Sandbox
from pydo.sandbox import NotFoundError, Snapshot

# Snapshot names are 1 to 63 lowercase letters, digits and hyphens. Make yours unique.
name = f"example-{int(time.time())}"

with Sandbox.create() as sbx:
    sbx.exec("echo saved state > /tmp/state.txt", check=True)

    snap = sbx.create_snapshot(name=name, ttl="1h")
    try:
        print("created :", snap.snapshot_id, snap.state)
        snap.wait_until_ready()  # polls until complete, raises on failure or timeout
        print("ready   :", snap.state)

        again = Snapshot.get(snap.snapshot_id)
        print("get     :", again.name, again.state)
        again.close()

        try:
            names = [s.name for s in Snapshot.list(sandbox_id=sbx.sandbox_id)]
            print("list    :", names)
        except NotFoundError:
            # Known on the internal test API: listing answers 404.
            print("list    : snapshot list is not available yet")
    finally:
        print("deleted :", snap.delete())  # always delete; snapshots cost storage
