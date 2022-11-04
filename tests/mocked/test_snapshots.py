"""Mock tests for the Snapshots API resource"""

import responses

from pydo import Client


@responses.activate
def test_snapshots_list(mock_client: Client, mock_client_url):
    """Mocks the snapshots list operation"""
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

    responses.add(responses.GET, f"{mock_client_url}/v2/snapshots", json=expected)
    list_resp = mock_client.snapshots.list()

    assert list_resp == expected


@responses.activate
def test_snapshots_get(mock_client: Client, mock_client_url):
    """Tests Retrieving an Existing Snapshot"""
    expected = {
        "snapshot": {
            "id": "6372321",
            "name": "web-01-1595954862243",
            "created_at": "2020-07-28T16:47:44Z",
            "regions": ["nyc3", "sfo3"],
            "min_disk_size": 25,
            "size_gigabytes": 2.34,
            "resource_id": "200776916",
            "resource_type": "droplet",
            "tags": ["web", "env:prod"],
        }
    }

    responses.add(
        responses.GET, f"{mock_client_url}/v2/snapshots/6372321", json=expected
    )

    get_resp = mock_client.snapshots.get(snapshot_id="6372321")

    assert get_resp == expected


@responses.activate
def test_snapshots_delete(mock_client: Client, mock_client_url):
    """Test Snapshots Delete"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/snapshots/6372321",
        status=204,
    )
    del_resp = mock_client.snapshots.delete(snapshot_id="6372321")

    assert del_resp is None
