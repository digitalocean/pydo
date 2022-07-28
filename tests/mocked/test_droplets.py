"""Mock tests for the droplets API resource."""
import pytest
import responses

from digitalocean import Client
from digitalocean import models
from digitalocean.models import Distribution


@responses.activate
def test_list(mock_client: Client, mock_client_url):
    """Mocks the droplets list operation."""
    expected = {
        "droplets": [
            {
                "id": 3164444,
                "name": "example.com",
                "memory": 1024,
                "vcpus": 1,
                "disk": 25,
                "locked": False,
                "status": "active",
                "kernel": None,
                "created_at": "2020-07-21T18:37:44.000Z",
                "features": ["backups", "private_networking", "ipv6"],
                "backup_ids": [53893572],
                "next_backup_window": {
                    "start": "2020-07-30T00:00:00.000Z",
                    "end": "2020-07-30T23:00:00.000Z",
                },
                "snapshot_ids": [67512819],
                "image": {
                    "id": 63663980,
                    "name": "20.04 (LTS) x64",
                    "distribution": "Ubuntu",
                    "slug": "ubuntu-20-04-x64",
                    "public": True,
                    "regions": [
                        "ams2",
                        "ams3",
                        "blr1",
                        "fra1",
                        "lon1",
                        "nyc1",
                        "nyc2",
                        "nyc3",
                        "sfo1",
                        "sfo2",
                        "sfo3",
                        "sgp1",
                        "tor1",
                    ],
                    "created_at": "2020-05-15T05:47:50.000Z",
                    "type": "snapshot",
                    "min_disk_size": 20,
                    "size_gigabytes": 2.36,
                    "description": "",
                    "tags": [],
                    "status": "available",
                    "error_message": "",
                },
                "volume_ids": [],
                "size": {
                    "slug": "s-1vcpu-1gb",
                    "memory": 1024,
                    "vcpus": 1,
                    "disk": 25,
                    "transfer": 1,
                    "price_monthly": 5,
                    "price_hourly": 0.00743999984115362,
                    "regions": [
                        "ams2",
                        "ams3",
                        "blr1",
                        "fra1",
                        "lon1",
                        "nyc1",
                        "nyc2",
                        "nyc3",
                        "sfo1",
                        "sfo2",
                        "sfo3",
                        "sgp1",
                        "tor1",
                    ],
                    "available": True,
                    "description": "Basic",
                },
                "size_slug": "s-1vcpu-1gb",
                "networks": {
                    "v4": [
                        {
                            "ip_address": "10.128.192.124",
                            "netmask": "255.255.0.0",
                            "gateway": "nil",
                            "type": "private",
                        },
                        {
                            "ip_address": "192.241.165.154",
                            "netmask": "255.255.255.0",
                            "gateway": "192.241.165.1",
                            "type": "public",
                        },
                    ],
                    "v6": [
                        {
                            "ip_address": "2604:a880:0:1010::18a:a001",
                            "netmask": 64,
                            "gateway": "2604:a880:0:1010::1",
                            "type": "public",
                        }
                    ],
                },
                "region": {
                    "name": "New York 3",
                    "slug": "nyc3",
                    "features": [
                        "private_networking",
                        "backups",
                        "ipv6",
                        "metadata",
                        "install_agent",
                        "storage",
                        "image_transfer",
                    ],
                    "available": True,
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
                        "s-32vcpu-192g",
                    ],
                },
                "tags": ["web", "env:prod"],
                "vpc_uuid": "760e09ef-dc84-11e8-981e-3cfdfeaae000",
            }
        ],
        "links": {"pages": {}},
        "meta": {"total": 1},
    }
    responses.add(responses.GET, f"{mock_client_url}/v2/droplets", json=expected)
    list_resp = mock_client.droplets.list()

    assert len(list_resp) == 1
    assert list_resp[0].id == 3164444
    assert list_resp[0].name == "example.com"
    assert list_resp[0].image.distribution == Distribution.Ubuntu


@responses.activate
def test_create_single(mock_client: Client, mock_client_url):
    """Mocks the droplets create operation."""
    expected = {
        "droplet": {
            "id": 3164444,
            "name": "example.com",
            "memory": 1024,
            "vcpus": 1,
            "disk": 25,
            "locked": False,
            "status": "new",
            "kernel": None,
            "created_at": "2020-07-21T18:37:44.000Z",
            "features": [
                "backups",
                "private_networking",
                "ipv6",
                "monitoring",
            ],
            "backup_ids": [],
            "next_backup_window": None,
            "snapshot_ids": [],
            "image": {
                "id": 63663980,
                "name": "20.04 (LTS) x64",
                "distribution": "Ubuntu",
                "slug": "ubuntu-20-04-x64",
                "public": True,
                "regions": [
                    "ams2",
                    "ams3",
                    "blr1",
                    "fra1",
                    "lon1",
                    "nyc1",
                    "nyc2",
                    "nyc3",
                    "sfo1",
                    "sfo2",
                    "sfo3",
                    "sgp1",
                    "tor1",
                ],
                "created_at": "2020-05-15T05:47:50.000Z",
                "type": "snapshot",
                "min_disk_size": 20,
                "size_gigabytes": 2.36,
                "description": "",
                "tags": [],
                "status": "available",
                "error_message": "",
            },
            "volume_ids": [],
            "size": {
                "slug": "s-1vcpu-1gb",
                "memory": 1024,
                "vcpus": 1,
                "disk": 25,
                "transfer": 1,
                "price_monthly": 5,
                "price_hourly": 0.00743999984115362,
                "regions": [
                    "ams2",
                    "ams3",
                    "blr1",
                    "fra1",
                    "lon1",
                    "nyc1",
                    "nyc2",
                    "nyc3",
                    "sfo1",
                    "sfo2",
                    "sfo3",
                    "sgp1",
                    "tor1",
                ],
                "available": True,
                "description": "Basic",
            },
            "size_slug": "s-1vcpu-1gb",
            "networks": {"v4": [], "v6": []},
            "region": {
                "name": "New York 3",
                "slug": "nyc3",
                "features": [
                    "private_networking",
                    "backups",
                    "ipv6",
                    "metadata",
                    "install_agent",
                    "storage",
                    "image_transfer",
                ],
                "available": True,
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
                    "s-32vcpu-192g",
                ],
            },
            "tags": ["web", "env:prod"],
        },
        "links": {
            "actions": [
                {
                    "id": 7515,
                    "rel": "create",
                    "href": "https://api.digitalocean.com/v2/actions/7515",
                }
            ]
        },
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/droplets",
        json=expected,
        status=202,
    )
    single_create = models.DropletSingleCreate(
        name="example.com", region="nyc3", image="ubuntu-20-04-x64", size="s-1vcpu-1gb"
    )
    created_droplet, _ = mock_client.droplets.create(single_create)

    assert created_droplet.id == 3164444
    assert created_droplet.name == "example.com"
    assert created_droplet.region.slug == "nyc3"
    assert created_droplet.image.distribution == models.Distribution.Ubuntu


@responses.activate
def test_get(mock_client: Client, mock_client_url):
    """Mocks the droplets get operation."""
    expected = {
        "droplet": {
            "id": 3164444,
            "name": "example.com",
            "memory": 1024,
            "vcpus": 1,
            "disk": 25,
            "locked": False,
            "status": "active",
            "kernel": None,
            "created_at": "2020-07-21T18:37:44.000Z",
            "features": ["backups", "private_networking", "ipv6"],
            "backup_ids": [53893572],
            "next_backup_window": {
                "start": "2020-07-30T00:00:00.000Z",
                "end": "2020-07-30T23:00:00.000Z",
            },
            "snapshot_ids": [67512819],
            "image": {
                "id": 63663980,
                "name": "20.04 (LTS) x64",
                "distribution": "Ubuntu",
                "slug": "ubuntu-20-04-x64",
                "public": True,
                "regions": [
                    "ams2",
                    "ams3",
                    "blr1",
                    "fra1",
                    "lon1",
                    "nyc1",
                    "nyc2",
                    "nyc3",
                    "sfo1",
                    "sfo2",
                    "sfo3",
                    "sgp1",
                    "tor1",
                ],
                "created_at": "2020-05-15T05:47:50.000Z",
                "type": "snapshot",
                "min_disk_size": 20,
                "size_gigabytes": 2.36,
                "description": "",
                "tags": [],
                "status": "available",
                "error_message": "",
            },
            "volume_ids": [],
            "size": {
                "slug": "s-1vcpu-1gb",
                "memory": 1024,
                "vcpus": 1,
                "disk": 25,
                "transfer": 1,
                "price_monthly": 5,
                "price_hourly": 0.00743999984115362,
                "regions": [
                    "ams2",
                    "ams3",
                    "blr1",
                    "fra1",
                    "lon1",
                    "nyc1",
                    "nyc2",
                    "nyc3",
                    "sfo1",
                    "sfo2",
                    "sfo3",
                    "sgp1",
                    "tor1",
                ],
                "available": True,
                "description": "Basic",
            },
            "size_slug": "s-1vcpu-1gb",
            "networks": {
                "v4": [
                    {
                        "ip_address": "10.128.192.124",
                        "netmask": "255.255.0.0",
                        "gateway": "nil",
                        "type": "private",
                    },
                    {
                        "ip_address": "192.241.165.154",
                        "netmask": "255.255.255.0",
                        "gateway": "192.241.165.1",
                        "type": "public",
                    },
                ],
                "v6": [
                    {
                        "ip_address": "2604:a880:0:1010::18a:a001",
                        "netmask": 64,
                        "gateway": "2604:a880:0:1010::1",
                        "type": "public",
                    }
                ],
            },
            "region": {
                "name": "New York 3",
                "slug": "nyc3",
                "features": [
                    "private_networking",
                    "backups",
                    "ipv6",
                    "metadata",
                    "install_agent",
                    "storage",
                    "image_transfer",
                ],
                "available": True,
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
                    "s-32vcpu-192g",
                ],
            },
            "tags": ["web", "env:prod"],
            "vpc_uuid": "760e09ef-dc84-11e8-981e-3cfdfeaae000",
        }
    }
    responses.add(responses.GET, f"{mock_client_url}/v2/droplets/1", json=expected)
    get_resp = mock_client.droplets.get(1)

    assert get_resp == expected


@responses.activate
def test_delete(mock_client: Client, mock_client_url):
    """Mocks the droplets delete operation."""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/droplets/1",
        status=204,
    )

    del_resp = mock_client.droplets.destroy(1)

    assert del_resp is None
