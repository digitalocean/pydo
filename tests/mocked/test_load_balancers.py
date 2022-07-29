# pylint: disable=duplicate-code

"""Mock tests for the load balancers API resource."""
import responses

from digitalocean import Client


@responses.activate
def test_list_load_balancers(mock_client: Client, mock_client_url):
    """Mocks the load balancers list operation."""
    expected = {
        "load_balancers": [
            {
                "id": "a91a98de-9b5f-4198-91cd-f852e36f8265",
                "name": "example-lb-01",
                "ip": "138.197.58.110",
                "size": "lb-small",
                "size_unit": 1,
                "algorithm": "round_robin",
                "status": "active",
                "created_at": "2020-12-21T18:48:46Z",
                "forwarding_rules": [
                    {
                        "entry_protocol": "tcp",
                        "entry_port": 9701,
                        "target_protocol": "tcp",
                        "target_port": 30608,
                        "certificate_id": "",
                        "tls_passthrough": False,
                    },
                    {
                        "entry_protocol": "tcp",
                        "entry_port": 9702,
                        "target_protocol": "tcp",
                        "target_port": 32481,
                        "certificate_id": "",
                        "tls_passthrough": False,
                    },
                ],
                "health_check": {
                    "protocol": "tcp",
                    "port": 30608,
                    "path": "",
                    "check_interval_seconds": 3,
                    "response_timeout_seconds": 5,
                    "healthy_threshold": 5,
                    "unhealthy_threshold": 3,
                },
                "sticky_sessions": {"type": "none"},
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
                    "sizes": ["s-1vcpu-1gb", "s-1vcpu-1gb-amd", "s-1vcpu-1gb-intel"],
                },
                "tag": "",
                "droplet_ids": [298657533, 298658124],
                "redirect_http_to_https": False,
                "enable_proxy_protocol": False,
                "enable_backend_keepalive": False,
                "vpc_uuid": "953d698c-dc84-11e8-80bc-3cfdfea9fba1",
                "disable_lets_encrypt_dns_records": False,
            }
        ],
        "links": {},
        "meta": {"total": 1},
    }

    responses.add(responses.GET, f"{mock_client_url}/v2/load_balancers", json=expected)
    lbs = mock_client.load_balancers.list()

    assert lbs == expected


@responses.activate
def test_get_load_balancers(mock_client: Client, mock_client_url):
    """Mocks the load balancers get operation."""
    expected = {
        "load_balancer": {
            "id": "a91a98de-9b5f-4198-91cd-f852e36f8265",
            "name": "example-lb-01",
            "ip": "138.197.58.110",
            "size": "lb-small",
            "size_unit": 1,
            "algorithm": "round_robin",
            "status": "active",
            "created_at": "2020-12-21T18:48:46Z",
            "forwarding_rules": [
                {
                    "entry_protocol": "tcp",
                    "entry_port": 9701,
                    "target_protocol": "tcp",
                    "target_port": 30608,
                    "certificate_id": "",
                    "tls_passthrough": False,
                },
                {
                    "entry_protocol": "tcp",
                    "entry_port": 9702,
                    "target_protocol": "tcp",
                    "target_port": 32481,
                    "certificate_id": "",
                    "tls_passthrough": False,
                },
            ],
            "health_check": {
                "protocol": "tcp",
                "port": 30608,
                "path": "",
                "check_interval_seconds": 3,
                "response_timeout_seconds": 5,
                "healthy_threshold": 5,
                "unhealthy_threshold": 3,
            },
            "sticky_sessions": {"type": "none"},
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
                "sizes": ["s-1vcpu-1gb", "s-1vcpu-1gb-amd", "s-1vcpu-1gb-intel"],
            },
            "tag": "",
            "droplet_ids": [298657533, 298658124],
            "redirect_http_to_https": False,
            "enable_proxy_protocol": False,
            "enable_backend_keepalive": False,
            "vpc_uuid": "953d698c-dc84-11e8-80bc-3cfdfea9fba1",
            "disable_lets_encrypt_dns_records": False,
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/load_balancers/a91a98de-9b5f-4198-91cd-f852e36f8265",
        json=expected,
    )
    lb = mock_client.load_balancers.get(lb_id="a91a98de-9b5f-4198-91cd-f852e36f8265")

    assert lb == expected


@responses.activate
def test_create_load_balancers(mock_client: Client, mock_client_url):
    """Mocks the load balancers create operation."""
    expected = {
        "load_balancer": {
            "id": "a91a98de-9b5f-4198-91cd-f852e36f8265",
            "name": "example-lb-01",
            "ip": "",
            "size": "lb-small",
            "size_unit": 1,
            "algorithm": "round_robin",
            "status": "new",
            "created_at": "2020-12-21T18:48:46Z",
            "forwarding_rules": [
                {
                    "entry_protocol": "tcp",
                    "entry_port": 80,
                    "target_protocol": "tcp",
                    "target_port": 80,
                    "certificate_id": "",
                    "tls_passthrough": False,
                },
            ],
            "health_check": {
                "protocol": "tcp",
                "port": 80,
                "path": "",
                "check_interval_seconds": 3,
                "response_timeout_seconds": 5,
                "healthy_threshold": 5,
                "unhealthy_threshold": 3,
            },
            "sticky_sessions": {"type": "none"},
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
                "sizes": ["s-1vcpu-1gb", "s-1vcpu-1gb-amd", "s-1vcpu-1gb-intel"],
            },
            "tag": "",
            "droplet_ids": [298657533, 298658124],
            "redirect_http_to_https": False,
            "enable_proxy_protocol": False,
            "enable_backend_keepalive": False,
            "vpc_uuid": "953d698c-dc84-11e8-80bc-3cfdfea9fba1",
            "disable_lets_encrypt_dns_records": False,
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/load_balancers",
        json=expected,
        status=202,
    )
    lb = mock_client.load_balancers.create(
        body={
            "name": "example-lb-01",
            "region": "nyc3",
            "forwarding_rules": [
                {
                    "entry_protocol": "tcp",
                    "entry_port": 80,
                    "target_protocol": "tcp",
                    "target_port": 80,
                }
            ],
            "droplet_ids": [298657533, 298658124],
        }
    )

    assert lb == expected


@responses.activate
def test_update_load_balancers(mock_client: Client, mock_client_url):
    """Mocks the load balancers get operation."""
    expected = {
        "load_balancer": {
            "id": "a91a98de-9b5f-4198-91cd-f852e36f8265",
            "name": "example-lb-01",
            "ip": "138.197.58.110",
            "size": "lb-small",
            "size_unit": 1,
            "algorithm": "round_robin",
            "status": "active",
            "created_at": "2020-12-21T18:48:46Z",
            "forwarding_rules": [
                {
                    "entry_protocol": "tcp",
                    "entry_port": 9701,
                    "target_protocol": "tcp",
                    "target_port": 30608,
                    "certificate_id": "",
                    "tls_passthrough": False,
                },
                {
                    "entry_protocol": "tcp",
                    "entry_port": 9702,
                    "target_protocol": "tcp",
                    "target_port": 32481,
                    "certificate_id": "",
                    "tls_passthrough": False,
                },
            ],
            "health_check": {
                "protocol": "tcp",
                "port": 30608,
                "path": "",
                "check_interval_seconds": 3,
                "response_timeout_seconds": 5,
                "healthy_threshold": 5,
                "unhealthy_threshold": 3,
            },
            "sticky_sessions": {"type": "none"},
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
                "sizes": ["s-1vcpu-1gb", "s-1vcpu-1gb-amd", "s-1vcpu-1gb-intel"],
            },
            "tag": "",
            "droplet_ids": [298657533, 298658124],
            "redirect_http_to_https": False,
            "enable_proxy_protocol": False,
            "enable_backend_keepalive": False,
            "vpc_uuid": "953d698c-dc84-11e8-80bc-3cfdfea9fba1",
            "disable_lets_encrypt_dns_records": False,
        }
    }

    body = {
        "name": "example-lb-01",
        "size_unit": 1,
        "forwarding_rules": [
            {
                "entry_protocol": "tcp",
                "entry_port": 9701,
                "target_protocol": "tcp",
                "target_port": 30608,
                "certificate_id": "",
                "tls_passthrough": False,
            },
            {
                "entry_protocol": "tcp",
                "entry_port": 9702,
                "target_protocol": "tcp",
                "target_port": 32481,
                "certificate_id": "",
                "tls_passthrough": False,
            },
        ],
        "health_check": {
            "protocol": "tcp",
            "port": 30608,
            "check_interval_seconds": 3,
            "response_timeout_seconds": 5,
            "healthy_threshold": 5,
            "unhealthy_threshold": 3,
        },
        "droplet_ids": [298657533, 298658124],
        "vpc_uuid": "953d698c-dc84-11e8-80bc-3cfdfea9fba1",
    }

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/load_balancers/a91a98de-9b5f-4198-91cd-f852e36f8265",
        json=expected,
    )
    lb = mock_client.load_balancers.update(
        lb_id="a91a98de-9b5f-4198-91cd-f852e36f8265", body=body
    )

    assert lb == expected


@responses.activate
def test_delete_load_balancers(mock_client: Client, mock_client_url):
    """Mocks the load balancers delete operation."""
    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/load_balancers/a91a98de-9b5f-4198-91cd-f852e36f8265",
        status=204,
    )
    mock_client.load_balancers.delete(lb_id="a91a98de-9b5f-4198-91cd-f852e36f8265")


@responses.activate
def test_load_balancers_add_droplet(mock_client: Client, mock_client_url):
    """Mocks the load balancers add Droplet operation."""
    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/load_balancers/a91a98de-9b5f-4198-91cd-f852e36f8265/droplets",
        status=204,
    )
    mock_client.load_balancers.add_droplets(
        lb_id="a91a98de-9b5f-4198-91cd-f852e36f8265",
        body={"droplet_ids": [3164444]},
    )


@responses.activate
def test_load_balancers_remove_droplet(mock_client: Client, mock_client_url):
    """Mocks the load balancers remove Droplet operation."""
    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/load_balancers/a91a98de-9b5f-4198-91cd-f852e36f8265/droplets",
        status=204,
    )
    mock_client.load_balancers.remove_droplets(
        lb_id="a91a98de-9b5f-4198-91cd-f852e36f8265",
        body={"droplet_ids": [3164444]},
    )


@responses.activate
def test_load_balancers_add_rule(mock_client: Client, mock_client_url):
    """Mocks the load balancers add rule operation."""
    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/load_balancers/a91a98de-9b5f-4198-91cd-f852e36f8265/forwarding_rules",
        status=204,
    )
    mock_client.load_balancers.add_forwarding_rules(
        lb_id="a91a98de-9b5f-4198-91cd-f852e36f8265",
        body={
            "forwarding_rules": [
                {
                    "entry_protocol": "https",
                    "entry_port": 443,
                    "target_protocol": "http",
                    "target_port": 80,
                    "certificate_id": "892071a0-bb95-49bc-8021-3afd67a210bf",
                }
            ]
        },
    )


@responses.activate
def test_load_balancers_remove_rule(mock_client: Client, mock_client_url):
    """Mocks the load balancers remoev rule operation."""
    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/load_balancers/a91a98de-9b5f-4198-91cd-f852e36f8265/forwarding_rules",
        status=204,
    )
    mock_client.load_balancers.remove_forwarding_rules(
        lb_id="a91a98de-9b5f-4198-91cd-f852e36f8265",
        body={
            "forwarding_rules": [
                {
                    "entry_protocol": "https",
                    "entry_port": 443,
                    "target_protocol": "http",
                    "target_port": 80,
                    "certificate_id": "892071a0-bb95-49bc-8021-3afd67a210bf",
                }
            ]
        },
    )
