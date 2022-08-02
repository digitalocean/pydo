""" test_snapshots.py
    Integration tests for snapshots.
"""

import uuid

from tests.integration import defaults
from tests.integration import shared
from digitalocean import Client


def test_snapshots(integration_client: Client):
    """Tests listing, retrieving, and deleting a snapshot.

    Creates a droplet and waits for its status to be `active`.
    Then creates a snapshot and retrieves it.
    Then lists all snapshots.
    Then, deletes the snapshots.
    """

    volume_req = {
        "size_gigabytes": 10,
        "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
        "description": "Snapshots testing",
        "region": defaults.REGION,
        "filesystem_type": "ext4",
    }

    with shared.with_test_volume(integration_client, **volume_req) as volume:
        vol_id = volume["volume"]["id"]
        expected_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
        vol_attach_resp = integration_client.volume_snapshots.create(
            volume_id=vol_id, body={"name": expected_name}
        )
        assert vol_attach_resp["snapshot"]["name"] == expected_name
        snapshot_id = vol_attach_resp["snapshot"]["id"]

        # list all snapshots
        list_resp = integration_client.snapshots.list()
        assert len(list_resp) > 0

        # get a snapshot
        get_resp = integration_client.snapshots.get(snapshot_id=snapshot_id)
        assert get_resp["snapshot"]["name"] == expected_name

        # delete a snapshot
        delete_resp = integration_client.snapshots.delete(snapshot_id=snapshot_id)
        assert delete_resp is None
