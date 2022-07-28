"""Mock tests for the account API resource."""
import pytest
import responses

from digitalocean import Client, custom_errors, models


@responses.activate
def test_get(mock_client: Client, mock_client_url):
    """Mocks the account get operation."""
    resp_json = {
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
    responses.add(responses.GET, f"{mock_client_url}/v2/account", json=resp_json)
    acct = mock_client.account.get()

    expected = models.Account(
        droplet_limit=25,
        floating_ip_limit=5,
        email="sammy@digitalocean.com",
        uuid="b6fr89dbf6d9156cace5f3c78dc9851d957381ef",
        email_verified=True,
        status=models.Status.active,
        status_message=" ",
        team=models.Team(
            uuid="5df3e3004a17e242b7c20ca6c9fc25b701a47ece", name="My Team"
        ),
    )

    assert acct == expected


@responses.activate
def test_account_get_unauthenticated(mock_client: Client, mock_client_url):
    """Mocks the account get operation expecting an unauthenticated response"""

    err_resp = {"id": "Unauthorized", "message": "Unable to authenticate you"}

    responses.add(responses.GET, f"{mock_client_url}/v2/account", json=err_resp)
    with pytest.raises(custom_errors.DigitaloceanAPIError):
        mock_client.account.get()
