""" test_droplets.py
    Integration tests for droplets.
"""

import uuid

from tests.integration import defaults
from tests.integration import shared
from digitalocean import Client, models


def test_droplet_attach_volume(integration_client: Client, public_key: bytes):
    """Tests attaching a volume to a droplet.

    Creates a droplet and waits for its status to be `active`.
    Then creates a volume.
    Then attaches the volume to the droplet and waits for the create action
    to complete.
    Then, detaches the volume.
    """
    droplet_req = models.DropletSingleCreate(
        name=f"{defaults.PREFIX}-{uuid.uuid4()}",
        region=defaults.REGION,
        size=defaults.DROPLET_SIZE,
        image=defaults.DROPLET_IMAGE,
    )  # pyright: ignore

    with shared.with_test_droplet(
        integration_client, public_key, droplet_req, wait=True
    ) as droplet_ctx:
        droplet: models.Droplet = droplet_ctx["droplet"]

        volume_req = {
            "size_gigabytes": 10,
            "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
            "description": "Block storage testing",
            "region": defaults.REGION,
            "filesystem_type": "ext4",
        }

        with shared.with_test_volume(integration_client, **volume_req) as volume:
            volume_id = volume["volume"]["id"]
            vol_attach_resp = integration_client.volume_actions.post_by_id(
                volume_id,
                {"type": "attach", "droplet_id": droplet.id},
            )
            shared.wait_for_action(integration_client, vol_attach_resp["action"]["id"])
            droplet_get_resp = integration_client.droplets.get(droplet.id)
            assert volume_id in droplet_get_resp["droplet"]["volume_ids"]

            vol_dettach_resp = integration_client.volume_actions.post_by_id(
                volume_id,
                {"type": "detach", "droplet_id": droplet.id},
            )
            shared.wait_for_action(integration_client, vol_dettach_resp["action"]["id"])
            droplet_get_resp = integration_client.droplets.get(droplet.id)
            assert volume_id not in droplet_get_resp["droplet"]["volume_ids"]
