"""Mock tests for the actions API resource"""
import responses

from pydo import Client


@responses.activate
def test_list(mock_client: Client, mock_client_url):
    """Mocks the actions list operation."""
    expected = {
        "actions": [
            {
                "id": 36804636,
                "status": "completed",
                "type": "create",
                "started_at": "2020-11-14T16:29:21Z",
                "completed_at": "2020-11-14T16:30:06Z",
                "resource_id": 3164444,
                "resource_type": "droplet",
                "region": {},
                "region_slug": "string",
            },
        ]
    }

    responses.add(responses.GET, f"{mock_client_url}/v2/actions", json=expected)
    list_resp = mock_client.actions.list()

    assert list_resp == expected


@responses.activate
def test_get(mock_client: Client, mock_client_url):
    """Mocks the actions get operation."""

    action_id = 36804636
    expected = {
        "actions": {
            "id": action_id,
            "status": "completed",
            "type": "create",
            "started_at": "2020-11-14T16:29:21Z",
            "completed_at": "2020-11-14T16:30:06Z",
            "resource_id": 3164444,
            "resource_type": "droplet",
            "region": {},
            "region_slug": "string",
        },
        "links": {
            "pages": {
                "first": "https://api.digitalocean.com/v2/account/keys?page=1",
                "prev": "https://api.digitalocean.com/v2/account/keys?page=2",
            }
        },
        "meta": {"total": 1},
    }

    responses.add(
        responses.GET, f"{mock_client_url}/v2/actions/{action_id}", json=expected
    )
    get_resp = mock_client.actions.get(action_id)

    assert get_resp == expected
