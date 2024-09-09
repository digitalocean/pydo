# pylint: disable=line-too-long
# pylint: disable=duplicate-code
"""Mock tests for the Image Actions API resource"""

import responses

from pydo import Client


@responses.activate
def test_image_actions_get(mock_client: Client, mock_client_url):
    """Tests Retrieving an Existing Image Action"""
    image_id = 7938269
    action_id = 36805527
    expected = {
        "action": {
            "id": action_id,
            "status": "in-progress",
            "type": "transfer",
            "started_at": "2014-11-14T16:42:45Z",
            "completed_at": None,
            "resource_id": image_id,
            "resource_type": "image",
            "region": {
                "name": "New York 3",
                "slug": "nyc3",
                "sizes": ["s-1vcpu-3gb", "m-1vcpu-8gb"],
                "features": ["private_networking", "image_transfer"],
                "available": True,
            },
            "region_slug": "nyc3",
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/images/{image_id}/actions/{action_id}",
        json=expected,
    )

    get_resp = mock_client.image_actions.get(image_id=image_id, action_id=action_id)
    # TODO (to remove):
    # 1. action_id is missing in openapi spec for Python in Request samples:
    # https://docs.digitalocean.com/reference/api/api-reference/#operation/imageActions_get
    # 2. image_id in Python Request samples is better be updated
    # with the value in response - 7938269 - to avoid confusion
    # Should we update openapi spec? Should the ticket be created for this update?

    assert get_resp == expected


@responses.activate
def test_image_actions_list(mock_client: Client, mock_client_url):
    """Mocks the image actions list operation"""
    image_id = 7555620
    expected = {
        "actions": [
            {
                "id": 29410565,
                "status": "completed",
                "type": "transfer",
                "started_at": "2014-07-25T15:04:21Z",
                "completed_at": "2014-07-25T15:10:20Z",
                "resource_id": image_id,
                "resource_type": "image",
                "region": {
                    "name": "New York 2",
                    "slug": "nyc2",
                    "sizes": ["s-1vcpu-3gb", "s-24vcpu-128gb"],
                    "features": ["private_networking", "image_transfer"],
                    "available": True,
                },
                "region_slug": "nyc2",
            }
        ],
        "links": {
            "pages": {
                "last": "https://api.digitalocean.com/v2/images/{image_id}/actions?page=5&per_page=1",
                "next": "https://api.digitalocean.com/v2/images/{image_id}/actions?page=2&per_page=1",
            }
        },
        "meta": {"total": 5},
    }

    responses.add(
        responses.GET, f"{mock_client_url}/v2/images/{image_id}/actions", json=expected
    )
    list_resp = mock_client.image_actions.list(image_id=image_id)
    # TODO:
    # 1. Go Request samples seems to be mising the call itself
    # 2. Python Request sample is missing image_id as an input parameter for a list call
    # https://docs.digitalocean.com/reference/api/api-reference/#operation/imageActions_list
    #
    # Can we include it to the ticket mentioned in test_image_actions_get TODO?

    assert list_resp == expected


@responses.activate
def test_image_actions_post(mock_client: Client, mock_client_url):
    """Mocks the image actions post operation."""
    image_id = 7938269
    expected = {
        "action": {
            "id": 36805527,
            "status": "in-progress",
            "type": "transfer",
            "started_at": "2014-11-14T16:42:45Z",
            "completed_at": None,
            "resource_id": image_id,
            "resource_type": "image",
            "region": {
                "name": "New York 3",
                "slug": "nyc3",
                "sizes": ["s-1vcpu-3gb", "s-24vcpu-128gb"],
                "features": ["private_networking", "image_transfer"],
                "available": True,
            },
            "region_slug": "nyc3",
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/images/{image_id}/actions",
        json=expected,
        status=201,
    )

    create_req = {"type": "convert"}
    post_resp = mock_client.image_actions.post(image_id=image_id, body=create_req)

    assert post_resp == expected
