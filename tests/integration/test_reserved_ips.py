# pylint: disable=duplicate-code

""" test_reserved_ips.py
    Integration tests for reserved IPs.
"""

import uuid

from tests.integration import defaults, shared
from pydo import Client


def test_reserved_ips(integration_client: Client, public_key: bytes):
    """Tests creating a reserved IP, assigning it to a Droplet, and deleting it."""
    droplet_req = {
        "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
        "region": defaults.REGION,
        "size": defaults.DROPLET_SIZE,
        "image": defaults.DROPLET_IMAGE,
    }

    with shared.with_test_droplet(
        integration_client, public_key, **droplet_req
    ) as droplet:
        try:
            # Create reserved IP
            new_rip = integration_client.reserved_ips.create(
                body={"region": defaults.REGION}
            )
            rip = new_rip["reserved_ip"]["ip"]
            assert rip is not None
            assert new_rip["reserved_ip"]["region"]["slug"] == defaults.REGION
            assert new_rip["reserved_ip"]["droplet"] is None

            # Ensure Droplet create is finished to prevent "Droplet already has
            # a pending event" error when assigning the reserved IP.
            shared.wait_for_action(
                integration_client, droplet["links"]["actions"][0]["id"]
            )

            # Assign reserved IP to a Droplet
            droplet_id = droplet["droplet"]["id"]
            assign_action = integration_client.reserved_ips_actions.post(
                reserved_ip=rip,
                body={"type": "assign", "droplet_id": droplet_id},
            )
            assert assign_action["action"]["type"] == "assign_ip"
            shared.wait_for_action(integration_client, assign_action["action"]["id"])

            assigned_rip = integration_client.reserved_ips.get(reserved_ip=rip)
            assert assigned_rip["reserved_ip"]["droplet"]["id"] == droplet_id

            # Unassign reserved IP
            unassign_action = integration_client.reserved_ips_actions.post(
                reserved_ip=rip,
                body={"type": "unassign"},
            )
            assert unassign_action["action"]["type"] == "unassign_ip"
            shared.wait_for_action(integration_client, unassign_action["action"]["id"])

            unassigned_rip = integration_client.reserved_ips.get(reserved_ip=rip)
            assert unassigned_rip["reserved_ip"]["droplet"] is None
            assert new_rip["reserved_ip"]["region"]["slug"] == defaults.REGION

        finally:
            # Delete reserved IP
            if rip is not None:
                integration_client.reserved_ips.delete(reserved_ip=rip)
