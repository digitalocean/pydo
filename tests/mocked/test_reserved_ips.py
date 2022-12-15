# pylint: disable=duplicate-code
"""Mock tests for the reserved IPs API resource."""
import responses
from responses import matchers

from pydo import Client

@responses.activate
def test_list_reserved_ips(mock_client: Client, mock_client_url):
    """Mocks the reserved IPs list operation."""
    expected = {
        "reserved_ips": [
            {
                "ip": "192.0.2.1",
                "droplet": None,
                "region": {
                    "name": "New York 3",
                    "slug": "nyc3",
                    "features": [
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
                        "s-1vcpu-1gb-amd",
                        "s-1vcpu-1gb-intel",
                    ],
                },
                "locked": False,
            },
            {
                "ip": "192.0.2.2",
                "droplet": {
                    "id": 292117696,
                    "name": "ubuntu-s-1vcpu-1gb-nyc3-01",
                    "memory": 1024,
                    "vcpus": 1,
                    "disk": 25,
                    "locked": False,
                    "status": "active",
                    "kernel": None,
                    "created_at": "2022-03-24T16:11:54Z",
                    "features": [
                        "monitoring",
                        "droplet_agent",
                        "ipv6",
                        "private_networking",
                    ],
                    "backup_ids": [],
                    "next_backup_window": None,
                    "snapshot_ids": [],
                    "image": {
                        "id": 101111514,
                        "name": "20.04 (LTS) x64",
                        "distribution": "Ubuntu",
                        "slug": None,
                        "public": False,
                        "regions": [],
                        "created_at": "2022-02-01T16:53:57Z",
                        "min_disk_size": 15,
                        "type": "base",
                        "size_gigabytes": 0.61,
                        "description": "Ubuntu 20.04 x86",
                        "tags": [],
                        "status": "retired",
                    },
                    "volume_ids": [],
                    "size": {
                        "slug": "s-1vcpu-1gb",
                        "memory": 1024,
                        "vcpus": 1,
                        "disk": 25,
                        "transfer": 1,
                        "price_monthly": 6,
                        "price_hourly": 0.00893,
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
                                "ip_address": "198.51.100.2",
                                "netmask": "255.255.240.0",
                                "gateway": "198.51.100.1",
                                "type": "public",
                            },
                            {
                                "ip_address": "10.132.246.148",
                                "netmask": "255.255.0.0",
                                "gateway": "10.132.0.1",
                                "type": "private",
                            },
                            {
                                "ip_address": "192.0.2.2",
                                "netmask": "255.255.252.0",
                                "gateway": "159.89.252.1",
                                "type": "public",
                            },
                        ],
                        "v6": [
                            {
                                "ip_address": "2604:a880:800:10::989:f001",
                                "netmask": 64,
                                "gateway": "2604:a880:800:10::1",
                                "type": "public",
                            }
                        ],
                    },
                    "region": {
                        "name": "New York 3",
                        "slug": "nyc3",
                        "features": [
                            "backups",
                            "ipv6",
                            "metadata",
                            "install_agent",
                            "storage",
                            "image_transfer",
                            "server_id",
                            "management_networking",
                        ],
                        "available": True,
                        "sizes": [
                            "s-1vcpu-1gb",
                            "s-1vcpu-1gb-amd",
                            "s-1vcpu-1gb-intel",
                        ],
                    },
                    "tags": ["awesome"],
                    "vpc_uuid": "953d698c-dc84-11e8-80bc-3cfdfea9fba1",
                },
                "region": {
                    "name": "New York 3",
                    "slug": "nyc3",
                    "features": [
                        "backups",
                        "ipv6",
                        "metadata",
                        "install_agent",
                        "storage",
                        "image_transfer",
                        "server_id",
                        "management_networking",
                    ],
                    "available": True,
                    "sizes": [
                        "s-1vcpu-1gb",
                        "s-1vcpu-1gb-amd",
                        "s-1vcpu-1gb-intel",
                    ],
                },
                "locked": False,
            },
            {
                "ip": "192.0.2.3",
                "droplet": None,
                "region": {
                    "name": "New York 3",
                    "slug": "nyc3",
                    "features": [
                        "backups",
                        "ipv6",
                        "metadata",
                        "install_agent",
                        "storage",
                        "image_transfer",
                        "server_id",
                        "management_networking",
                    ],
                    "available": True,
                    "sizes": [
                        "s-1vcpu-1gb",
                        "s-1vcpu-1gb-amd",
                        "s-1vcpu-1gb-intel",
                    ],
                },
                "locked": False,
            },
        ],
        "links": {},
        "meta": {"total": 3},
    }

    responses.add(responses.GET, f"{mock_client_url}/v2/reserved_ips", json=expected)
    rips = mock_client.reserved_ips.list()

    assert rips == expected

@responses.activate
def test_list_reserved_ips_with_pagination(mock_client: Client, mock_client_url):
    """Mocks the reserved IPs list operation."""
    expected = {
        "reserved_ips": [
            {
                "ip": "192.0.2.1",
                "droplet": None,
                "region": {
                    "name": "New York 3",
                    "slug": "nyc3",
                    "features": [
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
                        "s-1vcpu-1gb-amd",
                        "s-1vcpu-1gb-intel",
                    ],
                },
                "locked": False,
            },
            {
                "ip": "192.0.2.2",
                "droplet": {
                    "id": 292117696,
                    "name": "ubuntu-s-1vcpu-1gb-nyc3-01",
                    "memory": 1024,
                    "vcpus": 1,
                    "disk": 25,
                    "locked": False,
                    "status": "active",
                    "kernel": None,
                    "created_at": "2022-03-24T16:11:54Z",
                    "features": [
                        "monitoring",
                        "droplet_agent",
                        "ipv6",
                        "private_networking",
                    ],
                    "backup_ids": [],
                    "next_backup_window": None,
                    "snapshot_ids": [],
                    "image": {
                        "id": 101111514,
                        "name": "20.04 (LTS) x64",
                        "distribution": "Ubuntu",
                        "slug": None,
                        "public": False,
                        "regions": [],
                        "created_at": "2022-02-01T16:53:57Z",
                        "min_disk_size": 15,
                        "type": "base",
                        "size_gigabytes": 0.61,
                        "description": "Ubuntu 20.04 x86",
                        "tags": [],
                        "status": "retired",
                    },
                    "volume_ids": [],
                    "size": {
                        "slug": "s-1vcpu-1gb",
                        "memory": 1024,
                        "vcpus": 1,
                        "disk": 25,
                        "transfer": 1,
                        "price_monthly": 6,
                        "price_hourly": 0.00893,
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
                                "ip_address": "198.51.100.2",
                                "netmask": "255.255.240.0",
                                "gateway": "198.51.100.1",
                                "type": "public",
                            },
                            {
                                "ip_address": "10.132.246.148",
                                "netmask": "255.255.0.0",
                                "gateway": "10.132.0.1",
                                "type": "private",
                            },
                            {
                                "ip_address": "192.0.2.2",
                                "netmask": "255.255.252.0",
                                "gateway": "159.89.252.1",
                                "type": "public",
                            },
                        ],
                        "v6": [
                            {
                                "ip_address": "2604:a880:800:10::989:f001",
                                "netmask": 64,
                                "gateway": "2604:a880:800:10::1",
                                "type": "public",
                            }
                        ],
                    },
                    "region": {
                        "name": "New York 3",
                        "slug": "nyc3",
                        "features": [
                            "backups",
                            "ipv6",
                            "metadata",
                            "install_agent",
                            "storage",
                            "image_transfer",
                            "server_id",
                            "management_networking",
                        ],
                        "available": True,
                        "sizes": [
                            "s-1vcpu-1gb",
                            "s-1vcpu-1gb-amd",
                            "s-1vcpu-1gb-intel",
                        ],
                    },
                    "tags": ["awesome"],
                    "vpc_uuid": "953d698c-dc84-11e8-80bc-3cfdfea9fba1",
                },
                "region": {
                    "name": "New York 3",
                    "slug": "nyc3",
                    "features": [
                        "backups",
                        "ipv6",
                        "metadata",
                        "install_agent",
                        "storage",
                        "image_transfer",
                        "server_id",
                        "management_networking",
                    ],
                    "available": True,
                    "sizes": [
                        "s-1vcpu-1gb",
                        "s-1vcpu-1gb-amd",
                        "s-1vcpu-1gb-intel",
                    ],
                },
                "locked": False,
            },
            {
                "ip": "192.0.2.3",
                "droplet": None,
                "region": {
                    "name": "New York 3",
                    "slug": "nyc3",
                    "features": [
                        "backups",
                        "ipv6",
                        "metadata",
                        "install_agent",
                        "storage",
                        "image_transfer",
                        "server_id",
                        "management_networking",
                    ],
                    "available": True,
                    "sizes": [
                        "s-1vcpu-1gb",
                        "s-1vcpu-1gb-amd",
                        "s-1vcpu-1gb-intel",
                    ],
                },
                "locked": False,
            },
        ],
        "links": {
            "pages": {
                "first": "https://api.digitalocean.com/v2/reserved_ips?page=2&per_page=20",
                "last": "https://api.digitalocean.com/v2/reserved_ips?page=6&per_page=20",
            }
        },
        "meta": {"total": 6},
    }

    params = {"per_page": 20, "page": 1}
    responses.add(responses.GET, f"{mock_client_url}/v2/reserved_ips", json=expected, match=[matchers.query_param_matcher(params)])
    rips = mock_client.reserved_ips.list()

    assert rips == expected


@responses.activate
def test_get_reserved_ips(mock_client: Client, mock_client_url):
    """Mocks the reserved IPs get operation."""
    expected = {
        "reserved_ip": {
            "ip": "192.0.2.1",
            "droplet": None,
            "region": {
                "name": "New York 3",
                "slug": "nyc3",
                "features": [
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
                    "s-1vcpu-1gb-amd",
                    "s-1vcpu-1gb-intel",
                ],
            },
            "locked": False,
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/reserved_ips/192.0.2.1",
        json=expected,
    )
    rip = mock_client.reserved_ips.get(reserved_ip="192.0.2.1")

    assert rip == expected


@responses.activate
def test_create_reserved_ips(mock_client: Client, mock_client_url):
    """Mocks the reserved IPs create operation."""
    expected = {
        "reserved_ip": {
            "ip": "192.0.2.1",
            "droplet": None,
            "region": {
                "name": "New York 3",
                "slug": "nyc3",
                "features": [
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
                    "s-1vcpu-1gb-amd",
                    "s-1vcpu-1gb-intel",
                ],
            },
            "locked": False,
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/reserved_ips",
        json=expected,
        status=202,
    )
    rip = mock_client.reserved_ips.create(body={"region": "nyc3"})

    assert rip == expected


@responses.activate
def test_delete_reserved_ips(mock_client: Client, mock_client_url):
    """Mocks the reserved IPs delete operation."""
    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/reserved_ips/192.0.2.1",
        status=204,
    )
    mock_client.reserved_ips.delete(reserved_ip="192.0.2.1")


@responses.activate
def test_list_reserved_ips_actions(mock_client: Client, mock_client_url):
    """Mocks the reserved IPs actions list operation."""
    expected = {
        "actions": [
            {
                "id": 1492489780,
                "status": "completed",
                "type": "unassign_ip",
                "started_at": "2022-05-23T21:03:21Z",
                "completed_at": "2022-05-23T21:03:22Z",
                "resource_id": 2680918192,
                "resource_type": "reserved_ip",
                "region": {
                    "name": "New York 3",
                    "slug": "nyc3",
                    "features": [
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
                        "s-1vcpu-1gb-amd",
                        "s-1vcpu-1gb-intel",
                    ],
                },
                "region_slug": "nyc3",
            },
            {
                "id": 1453215653,
                "status": "completed",
                "type": "assign_ip",
                "started_at": "2022-04-04T15:54:43Z",
                "completed_at": "2022-04-04T15:54:46Z",
                "resource_id": 2680918192,
                "resource_type": "reserved_ip",
                "region": {
                    "name": "New York 3",
                    "slug": "nyc3",
                    "features": [
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
                        "s-1vcpu-1gb-amd",
                        "s-1vcpu-1gb-intel",
                    ],
                },
                "region_slug": "nyc3",
            },
            {
                "id": 1453215650,
                "status": "completed",
                "type": "reserve_ip",
                "started_at": "2022-04-04T15:54:43Z",
                "completed_at": "2022-04-04T15:54:43Z",
                "resource_id": 2680918192,
                "resource_type": "reserved_ip",
                "region": {
                    "name": "New York 3",
                    "slug": "nyc3",
                    "features": [
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
                        "s-1vcpu-1gb-amd",
                        "s-1vcpu-1gb-intel",
                    ],
                },
                "region_slug": "nyc3",
            },
        ],
        "links": {},
        "meta": {"total": 3},
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/reserved_ips/192.0.2.1/actions",
        json=expected,
    )
    actions = mock_client.reserved_ips_actions.list(reserved_ip="192.0.2.1")

    assert actions == expected


@responses.activate
def test_get_reserved_ips_actions(mock_client: Client, mock_client_url):
    """Mocks the reserved IPs actions get operation."""
    expected = {
        "action": {
            "id": 1492489780,
            "status": "completed",
            "type": "unassign_ip",
            "started_at": "2022-05-23T21:03:21Z",
            "completed_at": "2022-05-23T21:03:22Z",
            "resource_id": 2680918192,
            "resource_type": "reserved_ip",
            "region": {
                "name": "New York 3",
                "slug": "nyc3",
                "features": [
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
                    "s-1vcpu-1gb-amd",
                    "s-1vcpu-1gb-intel",
                ],
            },
            "region_slug": "nyc3",
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/reserved_ips/192.0.2.1/actions/1492489780",
        json=expected,
    )
    actions = mock_client.reserved_ips_actions.get(
        reserved_ip="192.0.2.1", action_id=1492489780
    )

    assert actions == expected


@responses.activate
def test_post_reserved_ips_actions(mock_client: Client, mock_client_url):
    """Mocks the reserved IPs actions post operation."""
    expected = {
        "action": {
            "id": 1492489780,
            "status": "in-progress",
            "type": "unassign_ip",
            "started_at": "2022-05-23T21:03:21Z",
            "completed_at": None,
            "resource_id": 2680918192,
            "resource_type": "reserved_ip",
            "region": {
                "name": "New York 3",
                "slug": "nyc3",
                "features": [
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
                    "s-1vcpu-1gb-amd",
                    "s-1vcpu-1gb-intel",
                ],
            },
            "region_slug": "nyc3",
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/reserved_ips/192.0.2.1/actions",
        json=expected,
        status=201,
    )
    action = mock_client.reserved_ips_actions.post(
        reserved_ip="192.0.2.1", body={"type": "unassign"}
    )

    assert action == expected
