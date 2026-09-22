"""Page backwards through a session's older event history.

A plain attach replays only the newest events the server keeps within its
replay budget, so long-lived sessions have history that never arrives on the
live feed. This walks further back a page at a time using ``before``, the same
way a UI would build scrollback.

Required env:
  DIGITALOCEAN_TOKEN
  SESSION_ID
  PYDO_AGENTS_ENDPOINT  (stage2: https://api.s2r1.internal.digitalocean.com)

Optional env:
  PAGE_SIZE   events per page (server default is 200)
  MAX_PAGES   stop after this many pages (default 5)
"""

import os
import sys

from pydo import Client

SESSION_ID = os.environ["SESSION_ID"]
PAGE_SIZE = int(os.environ.get("PAGE_SIZE", "50"))
MAX_PAGES = int(os.environ.get("MAX_PAGES", "5"))

client = Client(
    token=os.environ["DIGITALOCEAN_TOKEN"],
    agents_endpoint=os.environ.get("PYDO_AGENTS_ENDPOINT"),
)
sessions = client.agents.sessions

# Start from the oldest event of a bounded replay: that is the cursor for the
# page before it.
with sessions.stream(SESSION_ID, replay_only=True) as replay:
    recent = list(replay)

if not recent:
    print("session has no events to page back from", file=sys.stderr)
    raise SystemExit(0)

cursor = replay.oldest_event_id
print(f"replay returned {len(recent)} events, oldest={cursor}", file=sys.stderr)

older = []
for page_number in range(1, MAX_PAGES + 1):
    page = sessions.history_page(SESSION_ID, before=cursor, limit=PAGE_SIZE)
    older = page.events + older
    print(
        f"page {page_number}: {len(page.events)} events "
        f"(has_more={page.has_more}, next before={page.next_before})",
        file=sys.stderr,
    )
    if not page.has_more or not page.next_before:
        break
    cursor = page.next_before

print(f"\nfetched {len(older)} older events, oldest first:", file=sys.stderr)
for event in older:
    print(f"  {event.get('event_id')}  {event.get('type')}")
