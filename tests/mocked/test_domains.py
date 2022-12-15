# pylint: disable=duplicate-code
"""Mock tests for the domains API resource"""

import responses
from responses import matchers

from pydo import Client


@responses.activate
def test_create(mock_client: Client, mock_client_url):
    """Tests Record Creation"""
    expected = {"domain": {"name": "clienttest.com", "ttl": 1800, "zone_file": ""}}

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/domains",
        json=expected,
        status=201,
    )

    create_resp = mock_client.domains.create({"name": "clienttest.com"})

    assert create_resp == expected


@responses.activate
def test_get(mock_client: Client, mock_client_url):
    """Test Record Get by Name"""
    expected = {
        "domain": {
            "name": "clienttest.com",
            "ttl": 1800,
            "zone_file": """$ORIGIN clienttest.com.\n$TTL 1800\nclienttest.com. \
            IN SOA ns1.digitalocean.com. \
            hostmaster.clienttest.com. 1657812556 10800 3600 604800 1800\nclienttest.com. \
            1800 IN NS ns1.digitalocean.com. \
            \nclienttest.com. 1800 IN NS ns2.digitalocean.com.\nclienttest.com. \
            1800 IN NS ns3.digitalocean.com.\n""",
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/domains/clienttest.com",
        json=expected,
        status=200,
    )

    get_resp = mock_client.domains.get("clienttest.com")

    assert get_resp == expected


@responses.activate
def test_list_with_pagination(mock_client: Client, mock_client_url):
    """Test Record List"""
    expected = {
        "domains": [
            {
                "name": "clienttest.com",
                "ttl": 1800,
                "zone_file": """$ORIGIN clienttest.com.\n$TTL 1800\nclienttest.com. \
                IN SOA ns1.digitalocean.com. \
                hostmaster.clienttest.com. 1657812556 10800 3600 604800 1800\nclienttest.com. \
                1800 IN NS ns1.digitalocean.com. \
                \nclienttest.com. 1800 IN NS ns2.digitalocean.com.\nclienttest.com. \
                1800 IN NS ns3.digitalocean.com.\n""",
            },
        ],
        "links": {
            "pages": {
                "next": "https://api.digitalocean.com/v2/domains?page=2&per_page=20",
                "last": "https://api.digitalocean.com/v2/domains?page=6&per_page=20"
            }
        },
        "meta": {"total": 6},
    }

    params = {"per_page": 20, "page": 1}
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/domains",
        json=expected,
        status=200,
        match=[matchers.query_param_matcher(params)],
    )

    list_resp = mock_client.domains.list()

    assert list_resp == expected


@responses.activate
def test_delete(mock_client: Client, mock_client_url):
    """Test Domain Delete"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/domains/testtclient.com",
        status=204,
    )
    del_resp = mock_client.domains.delete("testtclient.com")

    assert del_resp is None


@responses.activate
def test_create_record(mock_client: Client, mock_client_url):
    """Test Record Create"""
    expected = {
        "domain_record": {
            "id": 324119029,
            "type": "A",
            "name": "ec.com",
            "data": "162.10.66.0",
            "priority": None,
            "port": None,
            "ttl": 1800,
            "weight": None,
            "flags": None,
            "tag": None,
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/domains/ec.com/records",
        json=expected,
        status=201,
    )

    create_resp = mock_client.domains.create_record(
        "ec.com",
        {
            "type": "A",
            "name": "ec.com",
            "data": "162.10.66.0",
            "priority": None,
            "port": None,
            "ttl": 1800,
            "weight": None,
            "flags": None,
            "tag": None,
        },
    )

    assert create_resp == expected

@responses.activate
def test_list(mock_client: Client, mock_client_url):
    """Test Record List"""
    expected = {
        "domains": [
            {
                "name": "clienttest.com",
                "ttl": 1800,
                "zone_file": """$ORIGIN clienttest.com.\n$TTL 1800\nclienttest.com. \
                IN SOA ns1.digitalocean.com. \
                hostmaster.clienttest.com. 1657812556 10800 3600 604800 1800\nclienttest.com. \
                1800 IN NS ns1.digitalocean.com. \
                \nclienttest.com. 1800 IN NS ns2.digitalocean.com.\nclienttest.com. \
                1800 IN NS ns3.digitalocean.com.\n""",
            },
        ],
        "links": {},
        "meta": {"total": 1},
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/domains",
        json=expected,
        status=200,
    )

    list_resp = mock_client.domains.list()

    assert list_resp == expected

@responses.activate
def test_list_records(mock_client: Client, mock_client_url):
    """Test Record Domain List"""
    expected = {
        "domain_records": [
            {
                "id": 324119029,
                "type": "A",
                "name": "ec.com",
                "data": "162.10.66.0",
                "priority": None,
                "port": None,
                "ttl": 1800,
                "weight": None,
                "flags": None,
                "tag": None,
            },
        ],
        "links": {},
        "meta": {"total": 1},
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/domains/ec.com/records",
        json=expected,
        status=200,
    )

    list_resp = mock_client.domains.list_records("ec.com")

    assert list_resp == expected

@responses.activate
def test_list_records_with_pagination(mock_client: Client, mock_client_url):
    """Test Record Domain List"""
    expected = {
        "domain_records": [
            {
                "id": 324119029,
                "type": "A",
                "name": "ec.com",
                "data": "162.10.66.0",
                "priority": None,
                "port": None,
                "ttl": 1800,
                "weight": None,
                "flags": None,
                "tag": None,
            },
        ],
        "links": {
            "pages": {
                "next": "https://api.digitalocean.com/v2/domains/ec.com/records?page=2&per_page=20",
                "last": "https://api.digitalocean.com/v2/domains/ec.com/records?page=3&per_page=20"
            }
        },
        "meta": {"total": 6},
    }

    params = {"per_page": 20, "page": 1}
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/domains/ec.com/records",
        json=expected,
        status=200, 
        match=[matchers.query_param_matcher(params)],
    )

    list_resp = mock_client.domains.list_records("ec.com")

    assert list_resp == expected


@responses.activate
def test_get_record(mock_client: Client, mock_client_url):
    """Test Record Domain Get"""

    expected = {
        "domain_record": {
            "id": 324119029,
            "type": "A",
            "name": "ec.com",
            "data": "162.10.66.0",
            "priority": None,
            "port": None,
            "ttl": 1800,
            "weight": None,
            "flags": None,
            "tag": None,
        },
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/domains/ec.com/records/324119029",
        json=expected,
        status=200,
    )

    get_resp = mock_client.domains.get_record("ec.com", 324119029)

    assert get_resp == expected


@responses.activate
def test_update_record(mock_client: Client, mock_client_url):
    """Test Record Domain Update"""
    expected = {
        "domain_record": {
            "id": 324119029,
            "type": "A",
            "name": "ec.com",
            "data": "162.10.66.0",
            "priority": None,
            "port": None,
            "ttl": 1800,
            "weight": None,
            "flags": None,
            "tag": None,
        },
    }

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/domains/ec.com/records/324119029",
        json=expected,
        status=200,
    )

    update_resp = mock_client.domains.update_record(
        "ec.com",
        324119029,
        {
            "name": "ec.com",
            "type": "A",
        },
    )

    assert update_resp == expected


@responses.activate
def test_patch_record(mock_client: Client, mock_client_url):
    """Test Record Domain Update"""
    expected = {
        "domain_record": {
            "id": 324119029,
            "type": "A",
            "name": "ec.com",
            "data": "162.10.66.0",
            "priority": None,
            "port": None,
            "ttl": 1800,
            "weight": None,
            "flags": None,
            "tag": None,
        },
    }

    responses.add(
        responses.PATCH,
        f"{mock_client_url}/v2/domains/ec.com/records/324119029",
        json=expected,
        status=200,
    )

    patch_resp = mock_client.domains.patch_record(
        "ec.com",
        324119029,
        {
            "name": "ec.com",
            "type": "A",
        },
    )

    assert patch_resp == expected


@responses.activate
def test_delete_record(mock_client: Client, mock_client_url):
    """Test Domain Record Delete"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/domains/ec.com/records/324119029",
        status=204,
    )

    del_resp = mock_client.domains.delete_record("ec.com", 324119029)

    assert del_resp is None
