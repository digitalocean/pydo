"""Placeholder mocked tests for Hosted Agents configs (MARSOHS-741).

Regeneration (blocked until openapi#1213 merges or a local SPEC_FILE is used):

1. Land https://github.com/digitalocean/openapi/pull/1213 (commit 867b2e7) —
   `/v2/agents/configs` list/get/create/delete + list sessions by config.
2. Either:
   - `workflow_dispatch` `.github/workflows/python-client-gen.yml` with the
     published openapi short SHA once the Spaces bundle exists, or
   - Locally: bundle the openapi PR tip, then
     `SPEC_FILE=/path/to/DigitalOcean-public.v2.yaml make generate`
3. Re-enable / extend these tests against the generated `Client.agents` surface.

Until Autorest regenerates operations from that SHA, these tests skip so CI stays green.
"""

from __future__ import annotations

import pytest
import responses

from pydo import Client

EXPECTED_LIST = {
    "configs": [
        {
            "id": "019fb39c-14d9-7080-933e-b9b90e25acda",
            "name": "support-agent",
            "agentspec_schema_version": "agents.digitalocean.com/v1alpha1",
            "content_hash": "75803fef24dc731824ecd4a1853c76153c7d8503534092b94da3ca3f31a882f4",
            "created_by": "user-1",
            "created_at": "2026-08-01T12:00:00Z",
            "updated_at": "2026-08-01T12:00:00Z",
        }
    ],
    "next_page_token": "",
}

EXPECTED_GET = {
    "config": {
        "id": "019fb39c-14d9-7080-933e-b9b90e25acda",
        "name": "support-agent",
        "agentspec_schema_version": "agents.digitalocean.com/v1alpha1",
        "manifest": {
            "apiVersion": "agents.digitalocean.com/v1alpha1",
            "kind": "Agent",
            "spec": {"runtime": {"adapter": "opencode"}},
        },
        "content_hash": "75803fef24dc731824ecd4a1853c76153c7d8503534092b94da3ca3f31a882f4",
        "created_by": "user-1",
        "created_at": "2026-08-01T12:00:00Z",
        "updated_at": "2026-08-01T12:00:00Z",
        "credentials": [
            {
                "name": "OPENAI_API_KEY",
                "source": "tenantSecret",
                "provider": "openai",
                "configured": True,
            }
        ],
    }
}

# Create returns the same config plus the manifest advisories. A get re-reads
# the same manifest but omits them, so they belong to this response only.
EXPECTED_CREATE = {
    "config": {
        **EXPECTED_GET["config"],
        "warnings": ["spec.unknownField is ignored by this schema version"],
    }
}


def _agents_config_operations_ready() -> bool:
    client = Client("", endpoint="https://testing.local")
    agents = getattr(client, "agents", None)
    return agents is not None and hasattr(agents, "list_configs")


pytestmark = pytest.mark.skipif(
    not _agents_config_operations_ready(),
    reason="awaiting Autorest regen from openapi@867b2e7 (digitalocean/openapi#1213)",
)


@responses.activate
def test_agents_list_configs(mock_client: Client, mock_client_url):
    """Mocks GET /v2/agents/configs."""
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/agents/configs",
        json=EXPECTED_LIST,
    )
    got = mock_client.agents.list_configs()
    assert got == EXPECTED_LIST
    assert got["configs"][0]["name"] == "support-agent"


@responses.activate
def test_agents_get_config(mock_client: Client, mock_client_url):
    """Mocks GET /v2/agents/configs/{config_id}."""
    config_id = "019fb39c-14d9-7080-933e-b9b90e25acda"
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/agents/configs/{config_id}",
        json=EXPECTED_GET,
    )
    got = mock_client.agents.get_config(config_id)
    assert got == EXPECTED_GET
    assert got["config"]["id"] == config_id


@responses.activate
def test_agents_create_config(mock_client: Client, mock_client_url):
    """Mocks POST /v2/agents/configs."""
    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/agents/configs",
        json=EXPECTED_CREATE,
        status=201,
    )
    got = mock_client.agents.create_config(
        {
            "name": "support-agent",
            "manifest_yaml": "apiVersion: agents.digitalocean.com/v1alpha1\nkind: Agent\n",
        }
    )
    assert got["config"]["name"] == "support-agent"
    assert got["config"]["warnings"]


@responses.activate
def test_agents_delete_config(mock_client: Client, mock_client_url):
    """Mocks DELETE /v2/agents/configs/{config_id}."""
    config_id = "019fb39c-14d9-7080-933e-b9b90e25acda"
    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/agents/configs/{config_id}",
        status=204,
    )
    mock_client.agents.delete_config(config_id)


@responses.activate
def test_agents_list_config_sessions(mock_client: Client, mock_client_url):
    """Mocks GET /v2/agents/configs/{config_id}/sessions."""
    config_id = "019fb39c-14d9-7080-933e-b9b90e25acda"
    expected = {"sessions": [], "next_page_token": ""}
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/agents/configs/{config_id}/sessions",
        json=expected,
    )
    # Method name follows Autorest naming once regen lands; try common variants.
    agents = mock_client.agents
    if hasattr(agents, "list_config_sessions"):
        got = agents.list_config_sessions(config_id)
    else:
        got = agents.list_sessions_by_config(config_id)
    assert got == expected
