from digitalocean import DigitalOceanClient


def test_account_get(integration_client: DigitalOceanClient):
    account_get_resp = integration_client.account.get()
    assert account_get_resp['account']['droplet_limit'] >= 25
