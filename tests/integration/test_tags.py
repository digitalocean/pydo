# pylint: disable=duplicate-code

""" test_tags.py
    Integration tests for tags.
"""

import uuid

from tests.integration import defaults, shared
from digitalocean import Client


def test_tag_droplet(integration_client: Client, public_key: bytes):
    """Tests tagging a Droplet.

    First,  it creates a tag.
    Then, it creates a Droplet and waits for its status to be `active`.
    Next, it tags the Droplet.
    Finally, it deletes the tag.
    """
    name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    create_body = {"name": name}

    with shared.with_test_tag(integration_client, **create_body) as tag:
        assert tag["tag"]["name"] == name

        get_resp = integration_client.tags.get(tag_id=name)
        assert get_resp["tag"]["name"] == name
        assert get_resp["tag"]["resources"]["count"] == 0

        droplet_req = {
            "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
            "region": defaults.REGION,
            "size": defaults.DROPLET_SIZE,
            "image": defaults.DROPLET_IMAGE,
        }

        with shared.with_test_droplet(
            integration_client, public_key, **droplet_req
        ) as droplet:
            shared.wait_for_action(
                integration_client, droplet["links"]["actions"][0]["id"]
            )
            droplet_id = droplet["droplet"]["id"]
            droplet_get_resp = integration_client.droplets.get(droplet_id)
            assert droplet_get_resp["droplet"]["status"] == "active"

            assign_req = {
                "resources": [
                    {
                        "resource_id": f"{droplet_id}",
                        "resource_type": "droplet",
                    },
                ]
            }

            integration_client.tags.assign_resources(
                tag_id=name,
                body=assign_req,
            )

            get_resp = integration_client.tags.get(tag_id=name)
            assert get_resp["tag"]["name"] == name
            assert (
                get_resp["tag"]["resources"]["last_tagged_uri"]
                == f"https://api.digitalocean.com/v2/droplets/{droplet_id}"
            )
            assert get_resp["tag"]["resources"]["count"] == 1
            assert get_resp["tag"]["resources"]["droplets"]["count"] == 1
