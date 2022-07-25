# pylint: disable=duplicate-code

""" test_firewalls.py
    Integration tests for firewalls.
"""

import uuid

from tests.integration import defaults, shared
from digitalocean import Client


def test_firewalls(integration_client: Client, public_key: bytes):
    """Tests creating, updating, and deleting a firewall"""
    tag_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    firewall_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    tag_body = {"name": tag_name}

    with shared.with_test_tag(integration_client, **tag_body):
        try:
            create_req = {
                "name": firewall_name,
                "outbound_rules": [
                    {
                        "protocol": "tcp",
                        "ports": "80",
                        "destinations": {"addresses": ["0.0.0.0/0", "::/0"]},
                    }
                ],
                "tags": [tag_name],
            }

            # Create firewall
            firewall = integration_client.firewalls.create(body=create_req)
            firewall_id = firewall["firewall"]["id"]
            assert firewall_id is not None
            assert firewall["firewall"]["name"] == firewall_name
            assert firewall["firewall"]["tags"] == [tag_name]
            assert firewall["firewall"]["outbound_rules"][0]["protocol"] == "tcp"
            assert firewall["firewall"]["outbound_rules"][0]["ports"] == "80"
            assert firewall["firewall"]["outbound_rules"][0]["destinations"] == {
                "addresses": ["0.0.0.0/0", "::/0"]
            }

            # GET firewall
            got = integration_client.firewalls.get(firewall_id=firewall_id)
            assert firewall_id == got["firewall"]["id"]
            assert got["firewall"]["name"] == firewall_name
            assert got["firewall"]["tags"] == [tag_name]
            assert got["firewall"]["outbound_rules"][0]["protocol"] == "tcp"
            assert got["firewall"]["outbound_rules"][0]["ports"] == "80"
            assert got["firewall"]["outbound_rules"][0]["destinations"] == {
                "addresses": ["0.0.0.0/0", "::/0"]
            }

            # Add rule
            rule = {
                "inbound_rules": [
                    {
                        "protocol": "tcp",
                        "ports": "2222",
                        "sources": {"addresses": ["0.0.0.0/0", "::/0"]},
                    }
                ]
            }
            integration_client.firewalls.add_rules(firewall_id=firewall_id, body=rule)
            updated = integration_client.firewalls.get(firewall_id=firewall_id)
            assert updated["firewall"]["inbound_rules"][0]["protocol"] == "tcp"
            assert updated["firewall"]["inbound_rules"][0]["ports"] == "2222"
            assert updated["firewall"]["inbound_rules"][0]["sources"] == {
                "addresses": ["0.0.0.0/0", "::/0"]
            }

            # Remove rule
            remove = {
                "outbound_rules": [
                    {
                        "protocol": "tcp",
                        "ports": "80",
                        "destinations": {"addresses": ["0.0.0.0/0", "::/0"]},
                    }
                ]
            }
            integration_client.firewalls.delete_rules(
                firewall_id=firewall_id, body=remove
            )
            removed = integration_client.firewalls.get(firewall_id=firewall_id)
            assert len(removed["firewall"]["outbound_rules"]) == 0

        finally:
            # Delete firewall
            if firewall_id is not None:
                integration_client.firewalls.delete(firewall_id=firewall_id)