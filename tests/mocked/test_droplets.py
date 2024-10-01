# pylint: disable=line-too-long
# pylint: disable=too-many-lines

"""Mock tests for the droplets API resource."""
import responses

from pydo import Client


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

    assert list_resp == expected


@responses.activate
def test_create(mock_client: Client, mock_client_url):
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
    create_resp = mock_client.droplets.create(
        {
            "name": "example.com",
            "region": "nyc3",
            "size": "s-1vcpu-1gb",
            "image": "ubuntu-20-04-x64",
        }
    )

    assert create_resp == expected


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


@responses.activate
def test_destroy_by_tag(mock_client: Client, mock_client_url):
    """Mocks the droplets destroy by tag operation."""

    tag_name = "awesome"

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/droplets?tag_name={tag_name}",
        status=204,
    )

    del_resp = mock_client.droplets.destroy_by_tag(tag_name=tag_name)

    assert del_resp is None


@responses.activate
def test_list_backups(mock_client: Client, mock_client_url):
    """Mocks the droplets list backups operation."""

    expected = {
        "backups": [
            {
                "id": 67539192,
                "name": "web-01- 2020-07-29",
                "distribution": "Ubuntu",
                "slug": None,
                "public": False,
                "regions": ["nyc3"],
                "created_at": "2020-07-29T01:44:35Z",
                "min_disk_size": 50,
                "size_gigabytes": 2.34,
                "type": "backup",
            }
        ],
        "links": {},
        "meta": {"total": 1},
    }
    droplet_id = 1

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets/{droplet_id}/backups",
        json=expected,
        status=200,
    )

    resp = mock_client.droplets.list_backups(droplet_id)

    assert expected == resp


@responses.activate
def test_get_backup_policy(mock_client: Client, mock_client_url):
    """Mocks the droplets get backup policy operation."""

    droplet_id = 1

    expected = {
        "policy": {
            "droplet_id": droplet_id,
            "backup_policy": {
                "plan": "weekly",
                "weekday": "SUN",
                "hour": 20,
                "window_length_hours": 4,
                "retention_period_days": 28,
            },
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets/{droplet_id}/backups/policy",
        json=expected,
        status=200,
    )

    resp = mock_client.droplets.get_backup_policy(droplet_id)

    assert expected == resp


@responses.activate
def test_list_backup_policies(mock_client: Client, mock_client_url):
    """Mocks the droplets list backup policies operation."""

    expected = {
        "policies": {
            "436444618": {
                "droplet_id": 436444618,
                "backup_enabled": False,
            },
            "444909706": {
                "droplet_id": 444909706,
                "backup_enabled": True,
                "backup_policy": {
                    "plan": "weekly",
                    "weekday": "SUN",
                    "hour": 20,
                    "window_length_hours": 4,
                    "retention_period_days": 28,
                },
            },
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets/backups/policies",
        json=expected,
        status=200,
    )

    resp = mock_client.droplets.list_backup_policies()

    assert expected == resp


@responses.activate
def test_list_snapshots(mock_client: Client, mock_client_url):
    """Mocks the droplets list snapshots operation."""

    expected = {
        "snapshots": [
            {
                "id": 6372721,
                "name": "web-01-1595954862243",
                "created_at": "2020-07-28T16:47:44Z",
                "regions": ["nyc3", "sfo3"],
                "min_disk_size": 30,
                "size_gigabytes": 2.34,
                "type": "snapshot",
            }
        ],
        "links": {},
        "meta": {"total": 1},
    }
    droplet_id = 3929391

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets/{droplet_id}/snapshots",
        json=expected,
        status=200,
    )

    resp = mock_client.droplets.list_snapshots(droplet_id)

    assert expected == resp


@responses.activate
def list_supported_backup_policies(mock_client: Client, mock_client_url):
    """Mocks the supported backup policies."""

    expected = {
        "supported_policies": [
            {
                "name": "weekly",
                "possible_window_starts": [],
                "window_length_hours": 2,
                "retention_period_days": 20,
            },
            {
                "name": "daily",
                "possible_window_starts": [],
                "window_length_hours": 3,
                "retention_period_days": 9,
            },
        ],
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets/backups/supported_policies",
        json=expected,
        status=200,
    )

    resp = mock_client.droplets.list_supported_backup_policies()

    assert expected == resp


@responses.activate
def test_list_kernels(mock_client: Client, mock_client_url):
    """Mocks the droplets list kernels operation."""

    expected = {
        "kernels": [
            {
                "id": 7515,
                "name": "DigitalOcean GrubLoader v0.2 (20160714)",
                "version": "2016.07.13-DigitalOcean_loader_Ubuntu",
            }
        ],
        "links": {
            "pages": {
                "next": "https://api.digitalocean.com/v2/droplets/3164444/kernels?page=2&per_page=1",
                "last": "https://api.digitalocean.com/v2/droplets/3164444/kernels?page=171&per_page=1",
            }
        },
        "meta": {"total": 171},
    }
    droplet_id = 3929391

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets/{droplet_id}/kernels",
        json=expected,
        status=200,
    )

    resp = mock_client.droplets.list_kernels(droplet_id)

    assert expected == resp


@responses.activate
def test_list_firewalls(mock_client: Client, mock_client_url):
    """Mocks the droplets list firewalls operation."""

    expected = {
        "firewalls": [
            {
                "id": "bb4b2611-3d72-467b-8602-280330ecd65c",
                "status": "succeeded",
                "created_at": "2020-05-23T21:24:00Z",
                "pending_changes": [
                    {"droplet_id": 8043964, "removing": True, "status": "waiting"}
                ],
                "name": "firewall",
                "droplet_ids": [89989, 33322],
                "tags": ["base-image", "prod"],
                "inbound_rules": [
                    {
                        "protocol": "udp",
                        "ports": "8000-9000",
                        "sources": {
                            "addresses": ["1.2.3.4", "18.0.0.0/8"],
                            "droplet_ids": [8282823, 3930392],
                            "load_balancer_uids": [
                                "4de7ac8b-495b-4884-9a69-1050c6793cd6"
                            ],
                            "tags": ["base-image", "dev"],
                        },
                    }
                ],
                "outbound_rules": [
                    {
                        "protocol": "tcp",
                        "ports": "7000-9000",
                        "destinations": {
                            "addresses": ["1.2.3.4", "18.0.0.0/8"],
                            "droplet_ids": [3827493, 213213],
                            "load_balancer_uids": [
                                "4de7ac8b-495b-4884-9a69-1050c6793cd6"
                            ],
                            "tags": ["base-image", "prod"],
                        },
                    }
                ],
            }
        ],
        "links": {"pages": {}},
        "meta": {"total": 1},
    }
    droplet_id = 3164444

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets/{droplet_id}/firewalls",
        json=expected,
        status=200,
    )

    resp = mock_client.droplets.list_firewalls(droplet_id)

    assert expected == resp


@responses.activate
def test_list_neighbors(mock_client: Client, mock_client_url):
    """Mocks the droplets delete operation."""

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
                "kernel": {
                    "id": 7515,
                    "name": "DigitalOcean GrubLoader v0.2 (20160714)",
                    "version": "2016.07.13-DigitalOcean_loader_Ubuntu",
                },
                "created_at": "2020-07-21T18:37:44Z",
                "features": ["backups", "private_networking", "ipv6"],
                "backup_ids": [53893572],
                "next_backup_window": {
                    "start": "2019-12-04T00:00:00Z",
                    "end": "2019-12-04T23:00:00Z",
                },
                "snapshot_ids": [67512819],
                "image": {
                    "id": 7555620,
                    "name": "Nifty New Snapshot",
                    "type": "snapshot",
                    "distribution": "Ubuntu",
                    "slug": "nifty1",
                    "public": True,
                    "regions": ["nyc1", "nyc2"],
                    "created_at": "2020-05-04T22:23:02Z",
                    "min_disk_size": 20,
                    "size_gigabytes": 2.34,
                    "description": " ",
                    "tags": ["base-image", "prod"],
                    "status": "NEW",
                    "error_message": " ",
                },
                "volume_ids": ["506f78a4-e098-11e5-ad9f-000f53306ae1"],
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
                            "ip_address": "104.236.32.182",
                            "netmask": "255.255.192.0",
                            "gateway": "104.236.0.1",
                            "type": "public",
                        }
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
        ]
    }
    droplet_id = 3164444

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets/{droplet_id}/neighbors",
        json=expected,
        status=200,
    )

    resp = mock_client.droplets.list_neighbors(droplet_id)

    assert expected == resp


@responses.activate
def test_list_associated_resources(mock_client: Client, mock_client_url):
    """Mocks the droplets delete operation."""

    expected = {
        "reserved_ips": [{"id": "6186916", "name": "45.55.96.47", "cost": "4.00"}],
        "floating_ips": [{"id": "6186916", "name": "45.55.96.47", "cost": "4.00"}],
        "snapshots": [
            {
                "id": "61486916",
                "name": "ubuntu-s-1vcpu-1gb-nyc1-01-1585758823330",
                "cost": "0.05",
            }
        ],
        "volumes": [
            {
                "id": "ba49449a-7435-11ea-b89e-0a58ac14480f",
                "name": "volume-nyc1-01",
                "cost": "10.00",
            }
        ],
        "volume_snapshots": [
            {
                "id": "edb0478d-7436-11ea-86e6-0a58ac144b91",
                "name": "volume-nyc1-01-1585758983629",
                "cost": "0.04",
            }
        ],
    }
    droplet_id = 3164444

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets/{droplet_id}/destroy_with_associated_resources",
        json=expected,
        status=200,
    )

    resp = mock_client.droplets.list_associated_resources(droplet_id)

    assert expected == resp
