# pylint: disable=duplicate-code,line-too-long,too-many-locals
""" test_container_registry.py
    Integration tests for container registry.
"""

import uuid

from tests.integration import defaults
from pydo import Client


def test_container_registry(integration_client: Client):
    """Tests listing, retrieving, and deleting a container registry."""

    expected_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    container_registry_req = {
        "name": expected_name,
        "subscription_tier_slug": "basic",
        "region": defaults.REGION,
    }

    # delete a registry
    delete_resp = integration_client.registry.delete()
    assert delete_resp is None

    # create a registry
    container_registry_resp = integration_client.registry.create(
        body=container_registry_req
    )
    assert container_registry_resp["registry"]["name"] == expected_name
    registry_name = container_registry_resp["registry"]["name"]

    # get docker credentials
    get_docker_resp = integration_client.registry.get_docker_credentials(
        read_write=True
    )
    assert get_docker_resp["auths"]["registry.digitalocean.com"]["auth"] is not None

    # get a registry
    get_resp = integration_client.registry.get()
    assert get_resp["registry"]["name"] == expected_name
    registry_name = get_resp["registry"]["name"]

    # get subscription information
    get_sub_resp = integration_client.registry.get_subscription()
    assert get_sub_resp["subscription"]["tier"]["slug"] == "basic"

    # update subscription tier
    update_sub_resp = integration_client.registry.update_subscription(
        {"tier_slug": "starter"}
    )
    assert update_sub_resp["subscription"]["tier"]["slug"] == "starter"

    # validate container registry name
    new_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    validate_name = integration_client.registry.validate_name({"name": new_name})
    assert validate_name is None

    # start a garbage collection
    garbage = integration_client.registry.run_garbage_collection(
        registry_name=registry_name
    )
    assert garbage["garbage_collection"]["status"] == "requested"

    # get active garbage collection
    garbage_active = integration_client.registry.get_garbage_collection(
        registry_name=registry_name
    )
    assert garbage_active["garbage_collection"]["registry_name"] == registry_name

    # list garbage collection
    garbage_list = integration_client.registry.list_garbage_collections(
        registry_name=registry_name
    )
    assert len(garbage_list["garbage_collections"]) > 0

    # list registry options
    registry_list_options = integration_client.registry.get_options()
    assert len(registry_list_options["options"]["available_regions"]) > 0

    # delete a registry
    delete_resp = integration_client.registry.delete()
    assert delete_resp is None
