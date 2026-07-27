"""Placeholder mocked tests for Hosted Agents sessions (MARSOHS-551).

Regeneration (blocked until openapi#1207 merges or a local SPEC_FILE is used):

1. Land https://github.com/digitalocean/openapi/pull/1207 (commit 1835a59) —
   `/v2/agents/sessions` + `session_origin` models.
2. Either:
   - `workflow_dispatch` `.github/workflows/python-client-gen.yml` with
     `openapi_short_sha=1835a59` once the Spaces-published bundle exists, or
   - Locally: bundle the openapi PR tip, then
     `SPEC_FILE=/path/to/DigitalOcean-public.v2.yaml make generate`
3. Re-enable / extend these tests against the generated `Client.agents` surface.
   Expected Origin wire: `session.origin.product` in
   {direct, simulation, evaluation}; ListSessions omits sim/eval server-side.

Until Autorest regenerates operations from that SHA, these tests skip so CI stays green.
"""

from __future__ import annotations

import pytest
import responses

from pydo import Client

EXPECTED_LIST = {
    "sessions": [
        {
            "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "name": "demo-agent",
            "status": "SESSION_STATUS_READY",
            "origin": {
                "product": "direct",
                "verified": True,
            },
        }
    ],
    "next_page_token": "",
}

EXPECTED_GET = {
    "session": {
        "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "name": "demo-agent",
        "status": "SESSION_STATUS_READY",
        "origin": {
            "product": "direct",
            "verified": True,
        },
    }
}


def _agents_operations_ready() -> bool:
    client = Client("", endpoint="https://testing.local")
    agents = getattr(client, "agents", None)
    return agents is not None and hasattr(agents, "list_sessions")


pytestmark = pytest.mark.skipif(
    not _agents_operations_ready(),
    reason="awaiting Autorest regen from openapi@1835a59 (digitalocean/openapi#1207)",
)


@responses.activate
def test_agents_list_sessions(mock_client: Client, mock_client_url):
    """Mocks GET /v2/agents/sessions including session.origin."""
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/agents/sessions",
        json=EXPECTED_LIST,
    )
    got = mock_client.agents.list_sessions()
    assert got == EXPECTED_LIST
    assert got["sessions"][0]["origin"]["product"] == "direct"


@responses.activate
def test_agents_get_session(mock_client: Client, mock_client_url):
    """Mocks GET /v2/agents/sessions/{session_id} including session.origin."""
    session_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/agents/sessions/{session_id}",
        json=EXPECTED_GET,
    )
    got = mock_client.agents.get_session(session_id)
    assert got == EXPECTED_GET
    assert got["session"]["origin"]["product"] == "direct"
