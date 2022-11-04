# pylint: disable=line-too-long
# pylint: disable=duplicate-code
"""Mock tests for the Images API resource"""

import responses

from pydo import Client


@responses.activate
def test_images_list(mock_client: Client, mock_client_url):
    """Mocks the images list operation"""
    expected = {
        "images": [
            {
                "id": 7555620,
                "name": "Nifty New Snapshot",
                "distribution": "Ubuntu",
                "slug": None,
                "public": False,
                "regions": ["nyc2", "nyc3"],
                "created_at": "2014-11-04T22:23:02Z",
                "type": "snapshot",
                "min_disk_size": 20,
                "size_gigabytes": 2.34,
                "description": "",
                "tags": [],
                "status": "available",
                "error_message": "",
            },
            {
                "id": 7555621,
                "name": "Another Snapshot",
                "distribution": "Ubuntu",
                "slug": None,
                "public": False,
                "regions": ["nyc2"],
                "created_at": "2014-11-04T22:23:02Z",
                "type": "snapshot",
                "min_disk_size": 20,
                "size_gigabytes": 2.34,
                "description": "",
                "tags": [],
                "status": "available",
                "error_message": "",
            },
            {
                "id": 63663980,
                "name": "20.04 (LTS) x64",
                "distribution": "Ubuntu",
                "slug": "ubuntu-20-04-x64",
                "public": True,
                "regions": ["nyc2", "nyc3"],
                "created_at": "2020-05-15T05:47:50Z",
                "type": "snapshot",
                "min_disk_size": 20,
                "size_gigabytes": 2.36,
                "description": "",
                "tags": [],
                "status": "available",
                "error_message": "",
            },
            {
                "id": 7555621,
                "name": "A custom image",
                "distribution": "Arch Linux",
                "slug": None,
                "public": False,
                "regions": ["nyc3"],
                "created_at": "2014-11-04T22:23:02Z",
                "type": "custom",
                "min_disk_size": 20,
                "size_gigabytes": 2.34,
                "description": "",
                "tags": [],
                "status": "available",
                "error_message": "",
            },
            {
                "id": 7555621,
                "name": "An APP image",
                "distribution": "Fedora",
                "slug": None,
                "public": False,
                "regions": ["nyc2", "nyc3"],
                "created_at": "2014-11-04T22:23:02Z",
                "type": "snapshot",
                "min_disk_size": 20,
                "size_gigabytes": 2.34,
                "description": "",
                "tags": [],
                "status": "available",
                "error_message": "",
            },
            {
                "id": 7555621,
                "name": "A simple tagged image",
                "distribution": "CentOS",
                "slug": None,
                "public": False,
                "regions": ["nyc2", "nyc3"],
                "created_at": "2014-11-04T22:23:02Z",
                "type": "snapshot",
                "min_disk_size": 20,
                "size_gigabytes": 2.34,
                "description": "",
                "tags": ["simple-image"],
                "status": "available",
                "error_message": "",
            },
        ],
        "links": {"pages": {}},
        "meta": {"total": 6},
    }

    responses.add(responses.GET, f"{mock_client_url}/v2/images", json=expected)
    list_resp = mock_client.images.list()

    assert list_resp == expected


@responses.activate
def test_images_get(mock_client: Client, mock_client_url):
    """Tests Retrieving an Existing Image"""
    expected = {
        "image": {
            "id": 6918990,
            "name": "14.04 x64",
            "distribution": "Ubuntu",
            "slug": "ubuntu-16-04-x64",
            "public": True,
            "regions": [
                "nyc1",
                "ams1",
                "sfo1",
                "nyc2",
                "ams2",
                "sgp1",
                "lon1",
                "nyc3",
                "ams3",
                "nyc3",
            ],
            "created_at": "2014-10-17T20:24:33Z",
            "min_disk_size": 20,
            "size_gigabytes": 2.34,
            "description": "",
            "tags": [],
            "status": "available",
            "error_message": "",
        }
    }

    responses.add(responses.GET, f"{mock_client_url}/v2/images/6918990", json=expected)

    get_resp = mock_client.images.get(image_id="6918990")

    assert get_resp == expected


@responses.activate
def test_images_delete(mock_client: Client, mock_client_url):
    """Test Images Delete"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/images/6372321",
        status=204,
    )
    del_resp = mock_client.images.delete(image_id="6372321")

    assert del_resp is None


@responses.activate
def test_images_update(mock_client: Client, mock_client_url):
    """Mocks the images update operation."""
    expected = {
        "image": {
            "id": 7938391,
            "name": "new-image-name",
            "distribution": "Ubuntu",
            "slug": None,
            "public": False,
            "regions": ["nyc3", "nyc3"],
            "created_at": "2014-11-14T16:44:03Z",
            "min_disk_size": 20,
            "size_gigabytes": 2.34,
            "description": "",
            "tags": [],
            "status": "available",
            "error_message": "",
        }
    }
    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/images/7938391",
        json=expected,
        status=200,
    )

    update = {
        "name": "Nifty New Snapshot",
        "distribution": "Ubuntu",
        "description": " ",
    }
    firewall = mock_client.images.update(body=update, image_id="7938391")

    assert firewall == expected


@responses.activate
def test_images_create(mock_client: Client, mock_client_url):
    """Mocks the images create operation."""
    expected = {
        "image": {
            "created_at": "2018-09-20T19:28:00Z",
            "description": "Cloud-optimized image w/ small footprint",
            "distribution": "Ubuntu",
            "error_message": "",
            "id": 38413969,
            "name": "ubuntu-18.04-minimal",
            "regions": [],
            "type": "custom",
            "tags": ["base-image", "prod"],
            "status": "NEW",
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/images",
        json=expected,
        status=202,
    )

    create_req = {
        "name": "ubuntu-18.04-minimal",
        "url": "http://cloud-images.ubuntu.com/minimal/releases/bionic/release/ubuntu-18.04-minimal-cloudimg-amd64.img",
        "distribution": "Ubuntu",
        "region": "nyc3",
        "description": "Cloud-optimized image w/ small footprint",
        "tags": ["base-image", "prod"],
    }
    firewall = mock_client.images.create_custom(body=create_req)

    assert firewall == expected
