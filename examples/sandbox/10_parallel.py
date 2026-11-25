"""Run three sandboxes at the same time.

    python examples/sandbox/10_parallel.py

You should see three lines, one per sandbox, each with its own id and output,
and all three sandboxes deleted at the end. It takes about as long as one.

Needs DIGITALOCEAN_ACCESS_TOKEN. Set DIGITALOCEAN_API_URL to use another API address.
"""

import time
from concurrent.futures import ThreadPoolExecutor

from pydo import Sandbox


def work(n):
    with Sandbox.create() as sbx:  # deleted when this function returns, even on error
        out = sbx.exec(f"echo job {n} on $(hostname)").stdout.strip()
        return sbx.sandbox_id, out


start = time.monotonic()
with ThreadPoolExecutor(max_workers=3) as pool:
    for sandbox_id, out in pool.map(work, [1, 2, 3]):
        print(sandbox_id, "->", out)
print(f"done in {time.monotonic() - start:.1f}s, all sandboxes deleted")
