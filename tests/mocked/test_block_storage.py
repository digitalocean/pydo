# pylint: disable=duplicate-code
"""Mock tests for the Block Storage API resource"""

import responses

from pydo import Client


@responses.activate
def test_block_storage_list(mock_client: Client, mock_client_url):
    """Mocks the block storage list operation"""
    expected = {
        "volumes": [
            {
                "id": "506f78a4-e098-11e5-ad9f-000f53306ae1",
                "region": {
                    "name": "New York 1",
                    "slug": "nyc1",
                    "sizes": [
                        "s-1vcpu-1gb",
                        "s-1vcpu-2gb",
                        "s-1vcpu-3gb",
                        "s-2vcpu-2gb",
                        "s-3vcpu-1gb",
                        "s-2vcpu-4gb",
                        "s-4vcpu-8gb",
                        "s-6vcpu-16gb",
                        "s-8vcpu-32gb",
                        "s-12vcpu-48gb",
                        "s-16vcpu-64gb",
                        "s-20vcpu-96gb",
                        "s-24vcpu-128gb",
                        "s-32vcpu-192gb",
                    ],
                    "features": ["private_networking", "backups", "ipv6", "metadata"],
                    "available": True,
                },
                "droplet_ids": [],
                "name": "example",
                "description": "Block store for examples",
                "size_gigabytes": 10,
                "created_at": "2016-03-02T17:00:49Z",
                "filesystem_type": "ext4",
                "filesystem_label": "example",
                "tags": ["aninterestingtag"],
            },
            {
                "id": "506f78a4-e098-11e5-ad9f-000f53305eb2",
                "region": {
                    "name": "New York 3",
                    "slug": "nyc3",
                    "sizes": [
                        "s-1vcpu-1gb",
                        "s-1vcpu-2gb",
                        "s-1vcpu-3gb",
                        "s-2vcpu-2gb",
                        "s-3vcpu-1gb",
                        "s-2vcpu-4gb",
                        "s-4vcpu-8gb",
                        "s-6vcpu-16gb",
                        "s-8vcpu-32gb",
                        "s-12vcpu-48gb",
                        "s-16vcpu-64gb",
                        "s-20vcpu-96gb",
                        "s-24vcpu-128gb",
                        "s-32vcpu-192gb",
                    ],
                    "features": ["private_networking", "backups", "ipv6", "metadata"],
                    "available": True,
                },
                "droplet_ids": [],
                "name": "example",
                "description": "Block store for examples",
                "size_gigabytes": 10,
                "created_at": "2016-03-02T17:01:49Z",
                "filesystem_type": "ext4",
                "filesystem_label": "example",
                "tags": ["aninterestingtag"],
            },
        ],
        "links": {},
        "meta": {"total": 2},
    }

    responses.add(responses.GET, f"{mock_client_url}/v2/volumes", json=expected)
    list_resp = mock_client.volumes.list()

    assert list_resp == expected


@responses.activate
def test_block_storage_create(mock_client: Client, mock_client_url):
    """Tests Creating a Block Storage Volume"""
    expected = {
        "volume": {
            "id": "506f78a4-e098-11e5-ad9f-000f53306ae1",
            "region": {
                "name": "New York 1",
                "slug": "nyc1",
                "sizes": [
                    "s-1vcpu-1gb",
                    "s-1vcpu-2gb",
                    "s-1vcpu-3gb",
                    "s-2vcpu-2gb",
                    "s-3vcpu-1gb",
                    "s-2vcpu-4gb",
                    "s-4vcpu-8gb",
                    "s-6vcpu-16gb",
                    "s-8vcpu-32gb",
                    "s-12vcpu-48gb",
                    "s-16vcpu-64gb",
                    "s-20vcpu-96gb",
                    "s-24vcpu-128gb",
                    "s-32vcpu-192gb",
                ],
                "features": ["private_networking", "backups", "ipv6", "metadata"],
                "available": True,
            },
            "droplet_ids": [],
            "name": "example",
            "description": "Block store for examples",
            "size_gigabytes": 10,
            "filesystem_type": "ext4",
            "filesystem_label": "example",
            "created_at": "2020-03-02T17:00:49Z",
        }
    }

    responses.add(
        responses.POST, f"{mock_client_url}/v2/volumes", json=expected, status=201
    )

    create_resp = mock_client.volumes.create(
        {
            "size_gigabytes": 10,
            "name": "ext4_example",
            "description": "Block store for examples",
            "region": "nyc1",
            "filesystem_type": "ext4",
            "filesystem_label": "ext4_volume_01",
        }
    )

    assert create_resp == expected


@responses.activate
def test_block_storage_delete_by_name(mock_client: Client, mock_client_url):
    """Test Block Storage Delete By Name"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/volumes?name=volname&region=nyc1",
        status=204,
    )
    del_resp = mock_client.volumes.delete_by_name(name="volname", region="nyc1")

    assert del_resp is None


@responses.activate
def test_block_storage_snapshots_get(mock_client: Client, mock_client_url):
    """Tests Retrieving an Existing block storage snapshot"""
    expected = {
        "snapshot": {
            "id": "8fa70202-873f-11e6-8b68-000f533176b1",
            "name": "big-data-snapshot1475261774",
            "regions": ["nyc1"],
            "created_at": "2020-09-30T18:56:14Z",
            "resource_id": "82a48a18-873f-11e6-96bf-000f53315a41",
            "resource_type": "volume",
            "min_disk_size": 10,
            "size_gigabytes": 10,
            "tags": ["aninterestingtag"],
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/volumes/snapshots/506f78a4-e098-11e5-ad9f-000f53306ae1",
        json=expected,
    )

    get_resp = mock_client.volume_snapshots.get_by_id(
        snapshot_id="506f78a4-e098-11e5-ad9f-000f53306ae1"
    )

    assert get_resp == expected


@responses.activate
def test_block_storage_snapshots_list(mock_client: Client, mock_client_url):
    """Mocks the block storage snapshots list operation"""
    expected = {
        "snapshots": [
            {
                "id": "6372321",
                "name": "web-01-1595954862243",
                "created_at": "2020-07-28T16:47:44Z",
                "regions": ["nyc3", "sfo3"],
                "resource_id": "200776916",
                "resource_type": "droplet",
                "min_disk_size": 25,
                "size_gigabytes": 2.34,
                "tags": ["web", "env:prod"],
            },
            {
                "id": "fbe805e8-866b-11e6-96bf-000f53315a41",
                "name": "pvc-01-1595954862243",
                "created_at": "2019-09-28T23:14:30Z",
                "regions": ["nyc1"],
                "resource_id": "89bcc42f-85cf-11e6-a004-000f53315871",
                "resource_type": "volume",
                "min_disk_size": 2,
                "size_gigabytes": 0.1008,
                "tags": ["k8s"],
            },
        ],
        "links": {},
        "meta": {"total": 2},
    }

    responses.add(
        responses.GET, f"{mock_client_url}/v2/volumes/1234/snapshots", json=expected
    )
    list_resp = mock_client.volume_snapshots.list(volume_id="1234")

    assert list_resp == expected


@responses.activate
def test_block_storage_get(mock_client: Client, mock_client_url):
    """Tests Retrieving an Existing Block Storage"""
    expected = {
        "volume": {
            "id": "506f78a4-e098-11e5-ad9f-000f53306ae1",
            "region": {
                "name": "New York 1",
                "slug": "nyc1",
                "sizes": [
                    "s-1vcpu-1gb",
                    "s-1vcpu-2gb",
                    "s-1vcpu-3gb",
                    "s-2vcpu-2gb",
                    "s-3vcpu-1gb",
                    "s-2vcpu-4gb",
                    "s-4vcpu-8gb",
                    "s-6vcpu-16gb",
                    "s-8vcpu-32gb",
                    "s-12vcpu-48gb",
                    "s-16vcpu-64gb",
                    "s-20vcpu-96gb",
                    "s-24vcpu-128gb",
                    "s-32vcpu-192gb",
                ],
                "features": ["private_networking", "backups", "ipv6", "metadata"],
                "available": True,
            },
            "droplet_ids": [],
            "name": "example",
            "description": "Block store for examples",
            "size_gigabytes": 10,
            "filesystem_type": "ext4",
            "filesystem_label": "example",
            "created_at": "2020-03-02T17:00:49Z",
        }
    }

    responses.add(responses.GET, f"{mock_client_url}/v2/volumes/1234", json=expected)

    get_resp = mock_client.volumes.get(volume_id="1234")

    assert get_resp == expected


@responses.activate
def test_block_storage_snapshots_delete(mock_client: Client, mock_client_url):
    """Test block storage Delete Snapshot"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/volumes/snapshots/6372321",
        status=204,
    )
    del_resp = mock_client.volume_snapshots.delete_by_id(snapshot_id=6372321)

    assert del_resp is None


@responses.activate
def test_block_storage_delete(mock_client: Client, mock_client_url):
    """Test block storage Delete"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/volumes/6372321",
        status=204,
    )
    del_resp = mock_client.volumes.delete(volume_id=6372321)

    assert del_resp is None


@responses.activate
def test_block_storage_snapshots_create(mock_client: Client, mock_client_url):
    """Tests Creating a Block Storage Snapshot"""
    expected = {
        "snapshot": {
            "id": "8fa70202-873f-11e6-8b68-000f533176b1",
            "name": "big-data-snapshot1475261774",
            "regions": ["nyc1"],
            "created_at": "2020-09-30T18:56:14Z",
            "resource_id": "82a48a18-873f-11e6-96bf-000f53315a41",
            "resource_type": "volume",
            "min_disk_size": 10,
            "size_gigabytes": 10,
            "tags": ["aninterestingtag"],
        }
    }
    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/volumes/1234/snapshots",
        json=expected,
        status=201,
    )

    create_resp = mock_client.volume_snapshots.create(
        volume_id=1234, body={"name": "big-data-snapshot1475261774"}
    )

    assert create_resp == expected

@responses.activate
def test_volume_actions_list(mock_client: Client, mock_client_url):
    """Tests retrieving all actions that have been executed on a volume"""
    expected = {
            "actions": [
                {
                "id": 72531856,
                "status": "completed",
                "type": "attach_volume",
                "started_at": "2020-11-21T21:51:09Z",
                "completed_at": "2020-11-21T21:51:09Z",
                "resource_type": "volume",
                "region": {
                    "name": "New York 1",
                    "slug": "nyc1",
                    "sizes": [
                    "s-1vcpu-1gb",
                    "s-1vcpu-2gb",
                    "s-1vcpu-3gb",
                    "s-2vcpu-2gb",
                    "s-3vcpu-1gb",
                    "s-2vcpu-4gb",
                    "s-4vcpu-8gb",
                    "s-6vcpu-16gb",
                    "s-8vcpu-32gb",
                    "s-12vcpu-48gb",
                    "s-16vcpu-64gb",
                    "s-20vcpu-96gb",
                    "s-24vcpu-128gb",
                    "s-32vcpu-192gb"
                    ],
                    "features": [
                    "private_networking",
                    "backups",
                    "ipv6",
                    "metadata"
                    ],
                    "available": True
                },
                "region_slug": "nyc1"
                }
            ],
            "links": {},
            "meta": {
                "total": 1
            }
        }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/volumes/7724db7c/actions",
        json=expected,
        status=200,
    )

    get_resp = mock_client.volume_actions.list(volume_id="7724db7c")

    assert get_resp == expected
