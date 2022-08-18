# pylint: disable=line-too-long
""" test_images.py
    Integration tests for images.
"""

import uuid

from tests.integration import defaults
from digitalocean import Client


def test_images(integration_client: Client):
    """Tests listing, retrieving, and deleting a image."""

    expected_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    image_req = {
        "name": expected_name,
        "url": "http://cloud-images.ubuntu.com/minimal/releases/bionic/release/ubuntu-18.04-minimal-cloudimg-amd64.img",
        "distribution": "Ubuntu",
        "region": "nyc3",
        "description": "Cloud-optimized image w/ small footprint",
        "tags": ["base-image", "prod"],
    }

    image_resp = integration_client.images.create_custom(body=image_req)
    assert image_resp["image"]["name"] == expected_name
    image_id = image_resp["image"]["id"]

    # list all images
    list_resp = integration_client.images.list()
    assert len(list_resp) > 0

    # list all images with prod tag
    list_resp = integration_client.images.list(tag_name="prod")
    assert len(list_resp) > 0
    assert list_resp["images"][0]["tag_name"] == "prod"

    # get an image
    get_resp = integration_client.images.get(image_id=image_id)
    assert get_resp["image"]["name"] == expected_name

    # update an image
    new_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    update_req = {"name": new_name, "distribution": "Ubuntu", "description": " "}
    update_resp = integration_client.images.update(body=update_req, image_id=image_id)
    assert update_resp["image"]["name"] == new_name

    # delete a snapshot
    delete_resp = integration_client.images.delete(image_id=image_id)
    assert delete_resp is None
