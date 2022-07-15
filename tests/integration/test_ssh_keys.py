""" test_ssh_keys.py
    Integration tests for SSH keys.
"""

from tests.integration import shared
from digitalocean import DigitalOceanClient


def test_ssh_keys(integration_client: DigitalOceanClient, public_key):
    """Tests creating and modifying SSH keys on a live account.

    First, it creates a key using the shared with_ssh_key contextmanager.
    Next, it tests GETing the key both by fingerprint and ID.
    Than, it updates the key's name.
    """
    client = integration_client
    with shared.with_ssh_key(client, public_key) as fingerprint:
        get_by_fingerprint = client.ssh_keys.get(fingerprint)
        assert get_by_fingerprint["ssh_key"]["fingerprint"] == fingerprint
        name = get_by_fingerprint["ssh_key"]["name"]
        key_id = get_by_fingerprint["ssh_key"]["id"]

        get_by_id = client.ssh_keys.get(key_id)
        assert get_by_id["ssh_key"]["fingerprint"] == fingerprint
        assert get_by_id["ssh_key"]["name"] == name

        new_name = name + "-updated"
        updated = client.ssh_keys.update(
            ssh_key_identifier=key_id, body={"name": new_name}
        )
        assert updated["ssh_key"]["name"] == new_name
