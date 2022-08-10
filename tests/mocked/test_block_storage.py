"""Mock tests for the Block Storage API resource"""

import responses

from digitalocean import Client


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
          "s-32vcpu-192gb"
        ],
        "features": [
          "private_networking",
          "backups",
          "ipv6",
          "metadata"
        ],
        "available": true
      },
      "droplet_ids": [],
      "name": "example",
      "description": "Block store for examples",
      "size_gigabytes": 10,
      "created_at": "2016-03-02T17:00:49Z",
      "filesystem_type": "ext4",
      "filesystem_label": "example",
      "tags": [
        "aninterestingtag"
      ]
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
      "droplet_ids": [],
      "name": "example",
      "description": "Block store for examples",
      "size_gigabytes": 10,
      "created_at": "2016-03-02T17:01:49Z",
      "filesystem_type": "ext4",
      "filesystem_label": "example",
      "tags": [
        "aninterestingtag"
      ]
    }
  ],
  "links": {},
  "meta": {
    "total": 2
  }
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
    "droplet_ids": [],
    "name": "example",
    "description": "Block store for examples",
    "size_gigabytes": 10,
    "filesystem_type": "ext4",
    "filesystem_label": "example",
    "created_at": "2020-03-02T17:00:49Z"
  }
}

    responses.add(
        responses.POST, f"{mock_client_url}/v2/volumes", json=expected
    )

    create_resp = mock_client.volumes.create(
{
  "size_gigabytes": 10,
  "name": "ext4_example",
  "description": "Block store for examples",
  "region": "nyc1",
  "filesystem_type": "ext4",
  "filesystem_label": "ext4_volume_01"
}
    )

    assert create_resp == expected


@responses.activate
def test_block_storage_delete(mock_client: Client, mock_client_url):
    """Test Block Storage Delete"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/volumes",
        status=204,
    )
    del_resp = mock_client.snapshots.delete(snapshot_id="6372321")

    assert del_resp is None
