import responses

from pydo import Client


@responses.activate
def tests_for_uptime_checkLists(mock_client: Client, mock_client_url):
    """Mocks the uptime checkLinst operations"""

    expected = {
        "checks": [
            {
                "id": "5a4981aa-9653-4bd1-bef5-d6bff52042e4",
                "name": "Landing page check",
                "type": "https",
                "target": "https://www.landingpage.com",
                "regions": [
                    "us_east",
                    "eu_west"
                ],
                "enabled": True
            }
        ],
        "links": {
            "pages": {
                "pages": {
                    "first": "https://api.digitalocean.com/v2/account/keys?page=1",
                    "prev": "https://api.digitalocean.com/v2/account/keys?page=2"
                }
            }
        },
        "meta": {
            "total": 1
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/uptime/checks",
        json=expected,
        status=200
    )
    get_res = mock_client.uptime.list_checks()
    assert get_res == expected


@responses.activate
def test_for_createNewCheck(mock_client: Client, mock_client_url):
    expected = {
        "check": {
            "id": "5a4981aa-9653-4bd1-bef5-d6bff52042e4",
            "name": "Landing page check",
            "type": "https",
            "target": "https://www.landingpage.com",
            "regions": [
                "us_east",
                "eu_west"
            ],
            "enabled": True
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/uptime/checks",
        json=expected,
        status=201
    )
    req = {
        "name": "Landing page check",
        "type": "https",
        "target": "https://www.landingpage.com",
        "regions": [
            "us_east",
            "eu_west"
        ],
        "enabled": True
    }

    post_res = mock_client.uptime.create_check(body=req)
    assert post_res == expected