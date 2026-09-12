"""Resolve HITL. Set DIGITALOCEAN_TOKEN, SESSION_ID, REQUEST_ID, and PYDO_AGENTS_ENDPOINT (stage2)."""

import os

from pydo import Client
from pydo.agents import HITLOutcome, ResolutionSource

SESSION_ID = os.environ["SESSION_ID"]
REQUEST_ID = os.environ["REQUEST_ID"]

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
client.agents.sessions.resolve_hitl(
    SESSION_ID,
    REQUEST_ID,
    outcome=HITLOutcome.APPROVE,
    source=ResolutionSource.OUT_OF_BAND,
)

print("ok", REQUEST_ID)
