"""Mock tests for the firewalls API resource."""
import responses

from pydo import Client


@responses.activate
def test_list_firewalls(mock_client: Client, mock_client_url):
    """Mocks the firewalls list operation."""
    expected = {
        "firewalls": [
            {
                "id": "e8721de7-ebd9-46ff-8b8d-f6cd14b2769b",
                "name": "public-access",
                "status": "succeeded",
                "inbound_rules": [],
                "outbound_rules": [
                    {
                        "protocol": "icmp",
                        "ports": "0",
                        "destinations": {"addresses": ["0.0.0.0/0", "::/0"]},
                    },
                    {
                        "protocol": "tcp",
                        "ports": "0",
                        "destinations": {"addresses": ["0.0.0.0/0", "::/0"]},
                    },
                    {
                        "protocol": "udp",
                        "ports": "0",
                        "destinations": {"addresses": ["0.0.0.0/0", "::/0"]},
                    },
                ],
                "created_at": "2021-10-11T19:04:13Z",
                "droplet_ids": [],
                "tags": ["public-access"],
                "pending_changes": [],
            },
            {
                "id": "fb6045f1-cf1d-4ca3-bfac-18832663025b",
                "name": "firewall",
                "status": "succeeded",
                "inbound_rules": [
                    {
                        "protocol": "tcp",
                        "ports": "80",
                        "sources": {
                            "load_balancer_uids": [
                                "4de7ac8b-495b-4884-9a69-1050c6793cd6"
                            ]
                        },
                    },
                    {
                        "protocol": "tcp",
                        "ports": "22",
                        "sources": {"tags": ["gateway"], "addresses": ["18.0.0.0/8"]},
                    },
                ],
                "created_at": "2017-05-23T21:23:59Z",
                "droplet_ids": [123456],
                "tags": [],
                "pending_changes": [],
            },
        ],
        "links": {},
        "meta": {"total": 2},
    }

    responses.add(responses.GET, f"{mock_client_url}/v2/firewalls", json=expected)
    firewalls = mock_client.firewalls.list()

    assert firewalls == expected


@responses.activate
def test_get_firewalls(mock_client: Client, mock_client_url):
    """Mocks the firewalls get operation."""
    expected = {
        "firewall": {
            "id": "fb6045f1-cf1d-4ca3-bfac-18832663025b",
            "name": "firewall",
            "status": "succeeded",
            "inbound_rules": [
                {
                    "protocol": "tcp",
                    "ports": "80",
                    "sources": {
                        "load_balancer_uids": ["4de7ac8b-495b-4884-9a69-1050c6793cd6"]
                    },
                },
                {
                    "protocol": "tcp",
                    "ports": "22",
                    "sources": {"tags": ["gateway"], "addresses": ["18.0.0.0/8"]},
                },
            ],
            "created_at": "2017-05-23T21:23:59Z",
            "droplet_ids": [123456],
            "tags": [],
            "pending_changes": [],
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/firewalls/fb6045f1-cf1d-4ca3-bfac-18832663025b",
        json=expected,
    )
    firewalls = mock_client.firewalls.get(
        firewall_id="fb6045f1-cf1d-4ca3-bfac-18832663025b"
    )

    assert firewalls == expected


@responses.activate
def test_create_firewalls(mock_client: Client, mock_client_url):
    """Mocks the firewalls create operation."""
    expected = {
        "firewall": {
            "id": "bb4b2611-3d72-467b-8602-280330ecd65c",
            "name": "firewall",
            "status": "waiting",
            "inbound_rules": [
                {
                    "protocol": "tcp",
                    "ports": "80",
                    "sources": {
                        "load_balancer_uids": ["4de7ac8b-495b-4884-9a69-1050c6793cd6"]
                    },
                },
                {
                    "protocol": "tcp",
                    "ports": "22",
                    "sources": {"tags": ["gateway"], "addresses": ["18.0.0.0/8"]},
                },
            ],
            "outbound_rules": [
                {
                    "protocol": "tcp",
                    "ports": "80",
                    "destinations": {"addresses": ["0.0.0.0/0", "::/0"]},
                }
            ],
            "created_at": "2017-05-23T21:24:00Z",
            "droplet_ids": [8043964],
            "tags": [],
            "pending_changes": [
                {"droplet_id": 8043964, "removing": False, "status": "waiting"}
            ],
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/firewalls",
        json=expected,
        status=202,
    )

    create_req = {
        "name": "firewall",
        "inbound_rules": [
            {
                "protocol": "tcp",
                "ports": "80",
                "sources": {
                    "load_balancer_uids": ["4de7ac8b-495b-4884-9a69-1050c6793cd6"]
                },
            },
            {
                "protocol": "tcp",
                "ports": "22",
                "sources": {"tags": ["gateway"], "addresses": ["18.0.0.0/8"]},
            },
        ],
        "outbound_rules": [
            {
                "protocol": "tcp",
                "ports": "80",
                "destinations": {"addresses": ["0.0.0.0/0", "::/0"]},
            }
        ],
        "droplet_ids": [8043964],
    }
    firewall = mock_client.firewalls.create(body=create_req)

    assert firewall == expected


@responses.activate
def test_update_firewalls(mock_client: Client, mock_client_url):
    """Mocks the firewalls update operation."""
    expected = {
        "firewall": {
            "id": "bb4b2611-3d72-467b-8602-280330ecd65c",
            "name": "frontend-firewall",
            "inbound_rules": [
                {
                    "protocol": "tcp",
                    "ports": "80",
                    "sources": {
                        "load_balancer_uids": ["4de7ac8b-495b-4884-9a69-1050c6793cd6"]
                    },
                },
                {
                    "protocol": "tcp",
                    "ports": "22",
                    "sources": {"tags": ["gateway"], "addresses": ["18.0.0.0/8"]},
                },
            ],
            "outbound_rules": [
                {
                    "protocol": "tcp",
                    "ports": "80",
                    "destinations": {"addresses": ["0.0.0.0/0", "::/0"]},
                }
            ],
            "created_at": "2020-05-23T21:24:00Z",
            "droplet_ids": [8043964],
            "tags": ["frontend"],
            "status": "waiting",
            "pending_changes": [
                {"droplet_id": 8043964, "removing": False, "status": "waiting"}
            ],
        }
    }
    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/firewalls/bb4b2611-3d72-467b-8602-280330ecd65c",
        json=expected,
        status=200,
    )

    update = {
        "name": "frontend-firewall",
        "inbound_rules": [
            {
                "protocol": "tcp",
                "ports": "8080",
                "sources": {
                    "load_balancer_uids": ["4de7ac8b-495b-4884-9a69-1050c6793cd6"]
                },
            },
            {
                "protocol": "tcp",
                "ports": "22",
                "sources": {"tags": ["gateway"], "addresses": ["18.0.0.0/8"]},
            },
        ],
        "outbound_rules": [
            {
                "protocol": "tcp",
                "ports": "8080",
                "destinations": {"addresses": ["0.0.0.0/0", "::/0"]},
            }
        ],
        "droplet_ids": [8043964],
        "tags": ["frontend"],
    }
    firewall = mock_client.firewalls.update(
        body=update, firewall_id="bb4b2611-3d72-467b-8602-280330ecd65c"
    )

    assert firewall == expected


@responses.activate
def test_delete_firewalls(mock_client: Client, mock_client_url):
    """Mocks the firewalls delete operation."""
    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/firewalls/aaa-bbb-111-ccc-222",
        status=204,
    )

    mock_client.firewalls.delete(firewall_id="aaa-bbb-111-ccc-222")


@responses.activate
def test_firewalls_assign_droplets(mock_client: Client, mock_client_url):
    """Mocks the firewalls add Droplets operation."""
    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/firewalls/aaa-bbb-111-ccc-222/droplets",
        status=204,
    )

    mock_client.firewalls.assign_droplets(
        firewall_id="aaa-bbb-111-ccc-222", body={"droplet_ids": [1234, 5678]}
    )


@responses.activate
def test_firewalls_delete_droplets(mock_client: Client, mock_client_url):
    """Mocks the firewalls remove Droplets operation."""
    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/firewalls/aaa-bbb-111-ccc-222/droplets",
        status=204,
    )

    mock_client.firewalls.delete_droplets(
        firewall_id="aaa-bbb-111-ccc-222", body={"droplet_ids": [1234, 5678]}
    )


@responses.activate
def test_firewalls_add_tags(mock_client: Client, mock_client_url):
    """Mocks the firewalls add tags operation."""
    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/firewalls/aaa-bbb-111-ccc-222/tags",
        status=204,
    )

    mock_client.firewalls.add_tags(
        firewall_id="aaa-bbb-111-ccc-222", body={"tags": ["frontend"]}
    )


@responses.activate
def test_firewalls_delete_tags(mock_client: Client, mock_client_url):
    """Mocks the firewalls delete tags operation."""
    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/firewalls/aaa-bbb-111-ccc-222/tags",
        status=204,
    )

    mock_client.firewalls.delete_tags(
        firewall_id="aaa-bbb-111-ccc-222", body={"tags": ["frontend"]}
    )


@responses.activate
def test_firewalls_add_rules(mock_client: Client, mock_client_url):
    """Mocks the firewalls add rules operation."""
    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/firewalls/aaa-bbb-111-ccc-222/rules",
        status=204,
    )

    rules = {
        "inbound_rules": [
            {"protocol": "tcp", "ports": "3306", "sources": {"droplet_ids": [49696269]}}
        ],
        "outbound_rules": [
            {
                "protocol": "tcp",
                "ports": "3306",
                "destinations": {"droplet_ids": [49696269]},
            }
        ],
    }

    mock_client.firewalls.add_rules(firewall_id="aaa-bbb-111-ccc-222", body=rules)


@responses.activate
def test_firewalls_delete_rules(mock_client: Client, mock_client_url):
    """Mocks the firewalls delete rules operation."""
    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/firewalls/aaa-bbb-111-ccc-222/rules",
        status=204,
    )

    rules = {
        "inbound_rules": [
            {"protocol": "tcp", "ports": "3306", "sources": {"droplet_ids": [49696269]}}
        ],
        "outbound_rules": [
            {
                "protocol": "tcp",
                "ports": "3306",
                "destinations": {"droplet_ids": [49696269]},
            }
        ],
    }

    mock_client.firewalls.delete_rules(firewall_id="aaa-bbb-111-ccc-222", body=rules)
