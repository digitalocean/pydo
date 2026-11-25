"""Find your sandboxes older than MAX_AGE_HOURS and delete them (dry run by default).

    python examples/sandbox/11_cleanup.py              # list only
    DELETE=1 python examples/sandbox/11_cleanup.py     # delete them
    MAX_AGE_HOURS=24 python examples/sandbox/11_cleanup.py

You should see one line per old sandbox, or "nothing to clean up".

Needs DIGITALOCEAN_ACCESS_TOKEN. Set DIGITALOCEAN_API_URL to use another API address.
"""

import os
from datetime import datetime, timedelta, timezone

from pydo import Sandbox

max_age = timedelta(hours=float(os.environ.get("MAX_AGE_HOURS", "1")))
delete = os.environ.get("DELETE") == "1"
cutoff = datetime.now(timezone.utc) - max_age

old = [s for s in Sandbox.list() if s.info.created_at and s.info.created_at < cutoff]
for sbx in old:
    age = datetime.now(timezone.utc) - sbx.info.created_at
    print(f"{sbx.sandbox_id}  {sbx.state}  {sbx.template}  age {age}")
    if delete:
        print("  deleted" if sbx.kill() else "  already gone")

if not old:
    print("nothing to clean up")
elif not delete:
    print(
        f"\n{len(old)} sandbox(es) older than {max_age}. Run again with DELETE=1 to delete them."
    )
