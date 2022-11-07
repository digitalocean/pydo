"""Mock tests for the CDN endpoints."""
import responses

from pydo import Client


@responses.activate
def test_create(mock_client: Client, mock_client_url):
    """Mock Create CDN"""
    expected = {
        "endpoint": {
            "id": "19f06b6a-3ace-4315-b086-499a0e521b76",
            "origin": "static-images.nyc3.digitaloceanspaces.com",
            "endpoint": "static-images.nyc3.cdn.digitaloceanspaces.com",
            "created_at": "2018-07-19T15:04:16Z",
            "ttl": 3600,
        }
    }

    responses.add(
        responses.POST, f"{mock_client_url}/v2/cdn/endpoints", json=expected, status=201
    )

    create_req = {"origin": "static-images.nyc3.digitaloceanspaces.com", "ttl": 3600}
    create_resp = mock_client.cdn.create_endpoint(create_req)

    assert create_resp == expected


@responses.activate
def test_list(mock_client: Client, mock_client_url):
    """Mock List CDN"""

    expected = {
        "endpoints": [
            {
                "id": "19f06b6a-3ace-4315-b086-499a0e521b76",
                "origin": "static-images.nyc3.digitaloceanspaces.com",
                "endpoint": "static-images.nyc3.cdn.digitaloceanspaces.com",
                "created_at": "2018-07-19T15:04:16Z",
                "certificate_id": "892071a0-bb95-49bc-8021-3afd67a210bf",
                "custom_domain": "static.example.com",
                "ttl": 3600,
            }
        ],
        "links": {},
        "meta": {"total": 1},
    }

    responses.add(
        responses.GET, f"{mock_client_url}/v2/cdn/endpoints", json=expected, status=200
    )

    list_resp = mock_client.cdn.list_endpoints()

    assert list_resp == expected


@responses.activate
def test_get(mock_client: Client, mock_client_url):
    """Mock Get CDN"""

    expected = {
        "endpoint": {
            "id": "1",
            "origin": "static-images.nyc3.digitaloceanspaces.com",
            "endpoint": "static-images.nyc3.cdn.digitaloceanspaces.com",
            "created_at": "2018-07-19T15:04:16Z",
            "ttl": 3600,
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/cdn/endpoints/1",
        json=expected,
        status=200,
    )

    get_resp = mock_client.cdn.get_endpoint("1")

    assert get_resp == expected


@responses.activate
def test_update(mock_client: Client, mock_client_url):
    """Mock Update CDN"""

    expected = {
        "endpoint": {
            "id": "1",
            "origin": "static-images.nyc3.digitaloceanspaces.com",
            "endpoint": "static-images.nyc3.cdn.digitaloceanspaces.com",
            "created_at": "2018-07-19T15:04:16Z",
            "ttl": 3600,
        }
    }

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/cdn/endpoints/1",
        json=expected,
        status=200,
    )

    update_req = {
        "ttl": 3600,
        "certificate_id": "892071a0-bb95-49bc-8021-3afd67a210bf",
        "custom_domain": "static.example.com",
    }

    update_resp = mock_client.cdn.update_endpoints("1", update_req)

    assert update_resp == expected


@responses.activate
def test_delete(mock_client: Client, mock_client_url):
    """Mock Delete CDN"""

    responses.add(responses.DELETE, f"{mock_client_url}/v2/cdn/endpoints/1", status=204)

    delete_resp = mock_client.cdn.delete_endpoint("1")

    assert delete_resp is None


@responses.activate
def test_purge(mock_client: Client, mock_client_url):
    """Mock Purge CDN"""

    responses.add(
        responses.DELETE, f"{mock_client_url}/v2/cdn/endpoints/1/cache", status=204
    )

    purge_req = {"files": ["path/to/image.png", "path/to/css/*"]}

    purge_resp = mock_client.cdn.purge_cache("1", purge_req)

    assert purge_resp is None
