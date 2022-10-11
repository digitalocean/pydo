# pylint: disable=duplicate-code
"""Mock tests for the VPCs resource"""

import responses

from pydo import Client


@responses.activate
def test_vpcs_create(mock_client: Client, mock_client_url):
    """Testing create a new VPC"""

    expected = {
        "vpc": {
            "name": "env.prod-vpc",
            "description": "VPC for production environment",
            "region": "nyc1",
            "ip_range": "10.10.10.0/24",
            "default": "true",
            "id": "5a4981aa-9653-4bd1-bef5-d6bff52042e4",
            "urn": "do:droplet:13457723",
            "created_at": "2020-03-13T19:20:47.442049222Z",
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/vpcs",
        json=expected,
        status=201,
    )

    create_resp = mock_client.vpcs.create(
        {
            "name": "env.prod-vpc",
            "description": "VPC for production environment",
            "region": "nyc1",
            "ip_range": "10.10.10.0/24",
        }
    )

    assert create_resp == expected


@responses.activate
def test_vpcs_list(mock_client: Client, mock_client_url):
    """Test VPCs List"""
    expected = {
        "vpcs": [
            {
                "name": "env.prod-vpc",
                "description": "VPC for production environment",
                "region": "nyc1",
                "ip_range": "10.10.10.0/24",
                "id": "5a4981aa-9653-4bd1-bef5-d6bff52042e4",
                "urn": "do:vpc:5a4981aa-9653-4bd1-bef5-d6bff52042e4",
                "default": "true",
                "created_at": "2020-03-13T19:20:47.442049222Z",
            },
        ],
        "links": {},
        "meta": {"total": 1},
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/vpcs",
        json=expected,
        status=200,
    )

    list_resp = mock_client.vpcs.list()

    assert list_resp == expected


@responses.activate
def test_get_vpcs(mock_client: Client, mock_client_url):
    """Test VPCs Get"""

    expected = {
        "vpc": {
            "name": "env.prod-vpc",
            "description": "VPC for production environment",
            "region": "nyc1",
            "ip_range": "10.10.10.0/24",
            "default": "True",
            "id": "5a4981aa-9653-4bd1-bef5-d6bff52042e4",
            "urn": "do:droplet:13457723",
            "created_at": "2020-03-13T19:20:47.442049222Z",
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/vpcs/5a4981aa-9653-4bd1-bef5-d6bff52042e4",
        json=expected,
        status=200,
    )

    get_resp = mock_client.vpcs.get(vpc_id="5a4981aa-9653-4bd1-bef5-d6bff52042e4")

    assert get_resp == expected


@responses.activate
def test_update_vpcs(mock_client: Client, mock_client_url):
    """Test VPCs Update"""
    expected = {
        "vpc": {
            "name": "env.prod-vpc",
            "description": "VPC for production environment",
            "region": "nyc1",
            "ip_range": "10.10.10.0/24",
            "default": "True",
            "id": "5a4981aa-9653-4bd1-bef5-d6bff52042e4",
            "urn": "do:droplet:13457723",
            "created_at": "2020-03-13T19:20:47.442049222Z",
        }
    }

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/vpcs/5a4981aa-9653-4bd1-bef5-d6bff52042e4",
        json=expected,
        status=200,
    )

    update_resp = mock_client.vpcs.update(
        vpc_id="5a4981aa-9653-4bd1-bef5-d6bff52042e4",
        body={
            "name": "env.prod-vpc",
            "description": "VPC for production environment",
            "default": "True",
        },
    )

    assert update_resp == expected


@responses.activate
def test_patch_vpcs(mock_client: Client, mock_client_url):
    """Test VPCs Patch Update"""
    expected = {
        "vpc": {
            "name": "env.prod-vpc",
            "description": "VPC for production environment",
            "region": "nyc1",
            "ip_range": "10.10.10.0/24",
            "default": "true",
            "id": "5a4981aa-9653-4bd1-bef5-d6bff52042e4",
            "urn": "do:droplet:13457723",
            "created_at": "2020-03-13T19:20:47.442049222Z",
        }
    }

    responses.add(
        responses.PATCH,
        f"{mock_client_url}/v2/vpcs/5a4981aa-9653-4bd1-bef5-d6bff52042e4",
        json=expected,
        status=200,
    )

    patch_resp = mock_client.vpcs.patch(
        vpc_id="5a4981aa-9653-4bd1-bef5-d6bff52042e4",
        body={
            "name": "env.prod-vpc",
            "description": "VPC for production environment",
            "default": "true",
        },
    )

    assert patch_resp == expected


@responses.activate
def test_delete_vpcs(mock_client: Client, mock_client_url):
    """Test VPCs Delete"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/vpcs/5a4981aa-9653-4bd1-bef5-d6bff52042e4",
        status=204,
    )

    del_resp = mock_client.vpcs.delete(vpc_id="5a4981aa-9653-4bd1-bef5-d6bff52042e4")

    assert del_resp is None


@responses.activate
def test_vpcs_list_members(mock_client: Client, mock_client_url):
    """Test VPCs List Members"""
    expected = {
        "members": [
            {
                "urn": "do:loadbalancer:fb294d78-d193-4cb2-8737-ea620993591b",
                "name": "nyc1-load-balancer-01",
                "created_at": "2020-03-13T19:30:48Z",
            },
            {
                "urn": "do:dbaas:13f7a2f6-43df-4c4a-8129-8733267ddeea",
                "name": "db-postgresql-nyc1-55986",
                "created_at": "2020-03-13T19:30:18Z",
            },
            {
                "urn": "do:kubernetes:da39d893-96e1-4e4d-971d-1fdda33a46b1",
                "name": "k8s-nyc1-1584127772221",
                "created_at": "2020-03-13T19:30:16Z",
            },
            {
                "urn": "do:droplet:86e29982-03a7-4946-8a07-a0114dff8754",
                "name": "ubuntu-s-1vcpu-1gb-nyc1-01",
                "created_at": "2020-03-13T19:29:20Z",
            },
        ],
        "links": {},
        "meta": {"total": 4},
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/vpcs/1/members",
        json=expected,
        status=200,
    )

    list_resp = mock_client.vpcs.list_members(vpc_id=1)

    assert list_resp == expected
