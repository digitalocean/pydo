"""Mock tests for the tags API resource."""
import responses
from responses import matchers

from digitalocean import Client


@responses.activate
def test_list_tags(mock_client: Client, mock_client_url):
    """Mocks the tags list operation."""
    expected = {
        "tags": [
            {
                "name": "tag-with-resources",
                "resources": {
                    "count": 3,
                    "last_tagged_uri": "https://api.digitalocean.com/v2/droplets/123",
                    "droplets": {
                        "count": 2,
                        "last_tagged_uri": "https://api.digitalocean.com/v2/droplets/123",
                    },
                    "images": {
                        "count": 1,
                        "last_tagged_uri": "https://api.digitalocean.com/v2/images/1234",
                    },
                    "volumes": {"count": 0},
                    "volume_snapshots": {"count": 0},
                    "databases": {"count": 0},
                },
            },
            {
                "name": "tag-with-no-resources",
                "resources": {
                    "count": 0,
                    "droplets": {"count": 0},
                    "images": {"count": 0},
                    "volumes": {"count": 0},
                    "volume_snapshots": {"count": 0},
                    "databases": {"count": 0},
                },
            },
        ],
        "links": {},
        "meta": {"total": 2},
    }

    responses.add(responses.GET, f"{mock_client_url}/v2/tags", json=expected)
    tags = mock_client.tags.list()

    assert tags == expected


@responses.activate
def test_list_tags_pagination(mock_client: Client, mock_client_url):
    """Mocks the tags list operation."""
    expected = {
        "tags": [
            {
                "name": "tag-with-resources",
                "resources": {
                    "count": 3,
                    "last_tagged_uri": "https://api.digitalocean.com/v2/droplets/123",
                    "droplets": {
                        "count": 2,
                        "last_tagged_uri": "https://api.digitalocean.com/v2/droplets/123",
                    },
                    "images": {
                        "count": 1,
                        "last_tagged_uri": "https://api.digitalocean.com/v2/images/1234",
                    },
                    "volumes": {"count": 0},
                    "volume_snapshots": {"count": 0},
                    "databases": {"count": 0},
                },
            },
            {
                "name": "tag-with-no-resources",
                "resources": {
                    "count": 0,
                    "droplets": {"count": 0},
                    "images": {"count": 0},
                    "volumes": {"count": 0},
                    "volume_snapshots": {"count": 0},
                    "databases": {"count": 0},
                },
            },
        ],
        "links": {
            "pages": {
                "next": "https://api.digitalocean.com/v2/tags?page=2",
                "last": "https://api.digitalocean.com/v2/tags?page=3",
            }
        },
        "meta": {"total": 6},
    }

    params = {"per_page": 2, "page": 2}
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/tags",
        json=expected,
        match=[matchers.query_param_matcher(params)],
    )
    tags = mock_client.tags.list(per_page=2, page=2)

    assert tags == expected


@responses.activate
def test_get_tag(mock_client: Client, mock_client_url):
    """Mocks the tags get operation."""
    expected = {
        "tag": {
            "name": "example-tag",
            "resources": {
                "count": 1,
                "last_tagged_uri": "https://api.digitalocean.com/v2/images/1234",
                "droplets": {"count": 0},
                "images": {
                    "count": 1,
                    "last_tagged_uri": "https://api.digitalocean.com/v2/images/1234",
                },
                "volumes": {"count": 0},
                "volume_snapshots": {"count": 0},
                "databases": {"count": 0},
            },
        }
    }

    responses.add(
        responses.GET, f"{mock_client_url}/v2/tags/example-tag", json=expected
    )
    tags = mock_client.tags.get(tag_id="example-tag")

    assert tags == expected


@responses.activate
def test_create_tag(mock_client: Client, mock_client_url):
    """Mocks the tags create operation."""
    expected = {
        "tag": {
            "name": "example-tag",
            "resources": {
                "count": 0,
                "droplets": {"count": 0},
                "images": {"count": 0},
                "volumes": {"count": 0},
                "volume_snapshots": {"count": 0},
                "databases": {"count": 0},
            },
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/tags",
        json=expected,
        status=201,
    )
    tag = mock_client.tags.create(body={"name": "example-tag"})

    assert tag == expected


@responses.activate
def test_delete_tag(mock_client: Client, mock_client_url):
    """Mocks the tags delete operation."""
    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/tags/example-tag",
        status=204,
    )

    mock_client.tags.delete(tag_id="example-tag")


@responses.activate
def test_assign_resources(mock_client: Client, mock_client_url):
    """Mocks the tags assign resources operation."""

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/tags/example-tag/resources",
        status=204,
    )

    req = {
        "resources": [
            {"resource_id": "1234", "resource_type": "droplet"},
            {"resource_id": "5678", "resource_type": "image"},
            {"resource_id": "aaa-bbb-ccc-111", "resource_type": "volume"},
        ]
    }

    mock_client.tags.assign_resources(tag_id="example-tag", body=req)


@responses.activate
def test_unassign_resources(mock_client: Client, mock_client_url):
    """Mocks the tags unassign resources operation."""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/tags/example-tag/resources",
        status=204,
    )

    req = {
        "resources": [
            {"resource_id": "1234", "resource_type": "droplet"},
            {"resource_id": "5678", "resource_type": "image"},
            {"resource_id": "aaa-bbb-ccc-111", "resource_type": "volume"},
        ]
    }

    mock_client.tags.unassign_resources(tag_id="example-tag", body=req)
