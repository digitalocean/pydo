"""Mock tests for the account API resource."""
import pytest
import responses
from aioresponses import aioresponses

from pydo import Client
from pydo.aio import Client as aioClient

EXPECTED_ACCOUNT = {
    "account": {
        "droplet_limit": 25,
        "floating_ip_limit": 5,
        "email": "sammy@digitalocean.com",
        "uuid": "b6fr89dbf6d9156cace5f3c78dc9851d957381ef",
        "email_verified": True,
        "status": "active",
        "status_message": " ",
        "team": {
            "uuid": "5df3e3004a17e242b7c20ca6c9fc25b701a47ece",
            "name": "My Team",
        },
    }
}


@responses.activate
def test_account_get(mock_client: Client, mock_client_url):
    """Mocks the account get operation."""

    responses.add(responses.GET, f"{mock_client_url}/v2/account", json=EXPECTED_ACCOUNT)
    acct = mock_client.account.get()

    assert acct == EXPECTED_ACCOUNT


@pytest.mark.asyncio
async def test_account_get_async(mock_aio_client: aioClient, mock_client_url):
    """Mocks the account get aio operation."""

    with aioresponses() as mock_resp:
        mock_resp.get(
            f"{mock_client_url}/v2/account", status=200, payload=EXPECTED_ACCOUNT
        )
        acct = await mock_aio_client.account.get()

        assert acct == EXPECTED_ACCOUNT
