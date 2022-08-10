""" test_block_storage.py
    Integration tests for block storage.
"""

import uuid

from tests.integration import defaults
from tests.integration import shared
from digitalocean import Client


def test_block_storage_snapshots(integration_client: Client):
    """Tests listing, retrieving, and deleting a block storage snapshot."""

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

        # create snapshot from volume
        vol_attach_resp = integration_client.volume_snapshots.create(
            volume_id=vol_id, body={"name": expected_name}
        )
        assert vol_attach_resp["snapshot"]["name"] == expected_name
        snap_id = vol_attach_resp["snapshot"]["id"]

        # list snapshots for a volume
        list_resp = integration_client.volume_snapshots.list(volume_id=vol_id)
        assert len(list_resp['snapshots']) > 0

        # get an existing snapshot of a volume
        get_resp = integration_client.volume_snapshots.get_by_id(snapshot_id=snap_id)
        assert get_resp["snapshot"]["name"] == expected_name

        # delete a volume snapshot
        delete_resp = integration_client.volume_snapshots.delete_by_id(snapshot_id=snap_id)
        assert delete_resp is None


def test_block_storage(integration_client: Client):
    """Tests listing, retrieving, and deleting a block storage."""

    volume_req = {
        "size_gigabytes": 10,
        "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
        "description": "Snapshots testing",
        "region": defaults.REGION,
        "filesystem_type": "ext4",
    }

    # create volume
    volume = integration_client.volumes.create(body=volume_req)
    volume_id = volume["volume"]["id"] or ""
    assert volume_id != ""

    # list volumes
    list_resp = integration_client.volumes.list()
    assert len(list_resp['volumes']) > 0

    # get an existing volume
    get_resp = integration_client.volumes.get(volume_id=volume_id)
    assert get_resp["volume"]["name"] == volume["volume"]["name"]
