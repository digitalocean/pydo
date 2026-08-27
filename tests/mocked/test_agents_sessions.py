"""Placeholder mocked tests for Hosted Agents sessions (MARSOHS-551, MARSOHS-1019).

Regeneration (blocked until openapi#1207 merges or a local SPEC_FILE is used):

1. Land https://github.com/digitalocean/openapi/pull/1207 (commit 1835a59) —
   `/v2/agents/sessions` + `session_origin` models (includes `session.warnings`).
2. Either:
   - `workflow_dispatch` `.github/workflows/python-client-gen.yml` with
     `openapi_short_sha=1835a59` once the Spaces-published bundle exists, or
   - Locally: bundle the openapi PR tip, then
     `SPEC_FILE=/path/to/DigitalOcean-public.v2.yaml make generate`
3. Re-enable / extend these tests against the generated `Client.agents` surface.
   Expected Origin wire: `session.origin.product` in
   {direct, simulation, evaluation}; ListSessions omits sim/eval server-side.
   CreateSession may also return `session.warnings` (manifest + policy advisories;
   populated on create only — MARSOHS-1019 adds policy fidelity warnings such as
   bare-wildcard bash `command: "*"` with `action: ask` on Codex CLI).

Until Autorest regenerates operations from that SHA, these tests skip so CI stays green.
"""

from __future__ import annotations

import pytest
import responses

from pydo import Client

POLICY_WARNING = (
    'permissions.rules (tool bash, match.command "*"): '
    "this pattern cannot be enforced per-command on this agent"
)

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

# Create returns advisories on the session object only; get/list omit warnings.
EXPECTED_CREATE = {
    "session": {
        **EXPECTED_GET["session"],
        "agent_kind": "AGENT_KIND_CODEX_CLI",
        "created_at": "2026-08-13T21:01:32Z",
        "last_event_at": "2026-08-13T21:04:50Z",
        "warnings": [POLICY_WARNING],
    }
}


def _agents_operations_ready() -> bool:
    client = Client("", endpoint="https://testing.local")
    agents = getattr(client, "agents", None)
    return agents is not None and hasattr(agents, "list_sessions")


def _agents_create_session_ready() -> bool:
    client = Client("", endpoint="https://testing.local")
    agents = getattr(client, "agents", None)
    return agents is not None and hasattr(agents, "create_session")


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


@pytest.mark.skipif(
    not _agents_create_session_ready(),
    reason="awaiting Autorest regen from openapi@1835a59 (digitalocean/openapi#1207)",
)
@responses.activate
def test_agents_create_session_decodes_warnings(mock_client: Client, mock_client_url):
    """Mocks POST /v2/agents/sessions returning create-time session.warnings."""
    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/agents/sessions",
        json=EXPECTED_CREATE,
        status=200,
    )
    got = mock_client.agents.create_session(
        body={"name": "demo-agent", "config_id": "019fb39c-14d9-7080-933e-b9b90e25acda"},
    )
    warnings = got["session"]["warnings"]
    assert len(warnings) == 1
    assert 'match.command "*"' in warnings[0]
