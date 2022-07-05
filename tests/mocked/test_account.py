import responses

from digitalocean import DigitalOceanClient


@responses.activate
def test_get(mock_client: DigitalOceanClient, mock_client_url):
    expected = {
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
                "name": "My Team"
            }
        }
    }
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/account",
        json=expected
    )
    acct = mock_client.account.get()

    assert acct == expected
