""" test_vpcs.py
    Integration Tests for VPCs
"""

import time
import uuid

from digitalocean import Client
from tests.integration import defaults
from tests.integration import shared


def test_vpcs_create(integration_client: Client):
    """Testing create a new VPC"""

    expected_name = f"{defaults.PREFIX}-{uuid.uuid4()}"

    create_req = {
        "name": expected_name,
        "description": "VPC for testing client gen",
        "region": "nyc1",
    }

    try:
        vpc = integration_client.vpcs.create(create_req)
        assert vpc["vpc"]["name"] == expected_name
    finally:
        integration_client.vpcs.delete(vpc["vpc"]["id"])


def test_vpcs_list(integration_client: Client):
    """Testing listing all VPCs"""

    with shared.with_test_vpc(integration_client) as vpc:
        list_res = integration_client.vpcs.list()
        assert len(list_res) > 0


def test_vpcs_get(integration_client: Client):
    """Testing GETting a VPC"""

    with shared.with_test_vpc(integration_client) as vpc:
        vpc_id = vpc["vpc"]["id"]
        get_res = integration_client.vpcs.get(vpc_id)
        assert get_res["vpc"]["id"] == vpc["vpc"]["id"]


def test_vpcs_update(integration_client: Client):
    """Testing updating a VPC"""

    updated_name = f"{defaults.PREFIX}-{uuid.uuid4()}"

    update_req = {
        "name": updated_name,
    }

    with shared.with_test_vpc(integration_client) as vpc:
        vpc_id = vpc["vpc"]["id"]
        update_res = integration_client.vpcs.update(vpc_id, body=update_req)
        assert update_res["vpc"]["name"] == updated_name


def test_vpcs_patch(integration_client: Client):
    """Testing patching a VPC (partial update)"""

    updated_name = f"{defaults.PREFIX}-{uuid.uuid4()}"

    update_req = {
        "name": updated_name,
    }

    with shared.with_test_vpc(integration_client) as vpc:
        vpc_id = vpc["vpc"]["id"]
        previous_description = vpc["vpc"]["description"]
        update_res = integration_client.vpcs.patch(vpc_id, body=update_req)
        # ensure name changed but descriptiond didn't.
        assert (
            update_res["vpc"]["name"] == updated_name
            and previous_description == update_res["vpc"]["description"]
        )


def test_vpcs_delete(integration_client: Client):
    """Testing delete a VPC"""

    with shared.with_test_vpc(integration_client) as vpc:
        vpc_id = vpc["vpc"]["id"]
        try:
            delete_res = integration_client.vpcs.delete(vpc_id)
        finally:
            # empty response body means successful request
            assert delete_res == None


def test_vpcs_list_members(integration_client: Client, public_key: bytes):
    """Testing listing members of a VPC"""

    expected_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    with shared.with_test_vpc(integration_client) as vpc:
        vpc_id = vpc["vpc"]["id"]
        droplet_req = {
            "name": expected_name,
            "region": defaults.REGION,
            "size": defaults.DROPLET_SIZE,
            "image": defaults.DROPLET_IMAGE,
            "vpc_uuid": vpc_id,
        }

        with shared.with_test_droplet(
            integration_client, public_key, **droplet_req
        ) as droplet:
            shared.wait_for_action(
                integration_client, droplet["links"]["actions"][0]["id"]
            )
            list_res = integration_client.vpcs.list_members(vpc_id)
            members = list_res["members"]
            assert members[0]["name"] == expected_name
        list_res = len(integration_client.vpcs.list_members(vpc_id)["members"])
        while list_res != 0:
            list_res = len(integration_client.vpcs.list_members(vpc_id)["members"])
