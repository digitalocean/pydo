# pylint: disable=duplicate-code
"""Mock Tests For Uptime Resources"""
import responses

from pydo import Client


@responses.activate
def test_uptime_check_lists_get(mock_client: Client, mock_client_url):
    """Mocks the uptime checkLinst operations"""

    expected = {
        "checks": [
            {
                "id": "5a4981aa-9653-4bd1-bef5-d6bff52042e4",
                "name": "Landing page check",
                "type": "https",
                "target": "https://www.landingpage.com",
                "regions": ["us_east", "eu_west"],
                "enabled": True,
            }
        ],
        "links": {
            "pages": {
                "pages": {
                    "first": "https://api.digitalocean.com/v2/account/keys?page=1",
                    "prev": "https://api.digitalocean.com/v2/account/keys?page=2",
                }
            }
        },
        "meta": {"total": 1},
    }

    responses.add(
        responses.GET, f"{mock_client_url}/v2/uptime/checks", json=expected, status=200
    )
    get_res = mock_client.uptime.list_checks()
    assert get_res == expected


@responses.activate
def test_uptime_check_state_get(mock_client: Client, mock_client_url):
    """Mock Uptime Check State"""
    expected = {
        "state": {
            "regions": {
                "us_east": {
                    "status": "UP",
                    "status_changed_at": "2022-03-17T22:28:51Z",
                    "thirty_day_uptime_percentage": 97.99,
                },
                "eu_west": {
                    "status": "UP",
                    "status_changed_at": "2022-03-17T22:28:51Z",
                    "thirty_day_uptime_percentage": 97.99,
                },
            },
            "previous_outage": {
                "region": "us_east",
                "started_at": "2022-03-17T18:04:55Z",
                "ended_at": "2022-03-17T18:06:55Z",
                "duration_seconds": 120,
            },
        }
    }
    check_id = "4de7ac8b-495b-4884-9a69-1050c6793cd6"
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/uptime/checks/{check_id}/state",
        json=expected,
        status=200,
    )

    get_res = mock_client.uptime.get_check_state(check_id)

    assert get_res == expected


@responses.activate
def test_update_check_put(mock_client: Client, mock_client_url):
    """Mock Uptime Check Update"""
    expected = {
        "check": {
            "id": "5a4981aa-9653-4bd1-bef5-d6bff52042e4",
            "name": "Landing page check",
            "type": "https",
            "target": "https://www.landingpage.com",
            "regions": ["us_east", "eu_west"],
            "enabled": True,
        }
    }
    check_id = "4de7ac8b-495b-4884-9a69-1050c6793cd6"
    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/uptime/checks/{check_id}",
        json=expected,
        status=200,
    )
    req = {
        "name": "Landing page check",
        "type": "https",
        "target": "https://www.landingpage.com",
        "regions": ["us_east", "eu_west"],
        "enabled": True,
    }

    put_res = mock_client.uptime.update_check(check_id, body=req)
    assert put_res == expected


@responses.activate
def test_list_all_alerts_get(mock_client: Client, mock_client_url):
    """Mock Uptime Check List All Alerts"""
    url = "https://hooks.slack.com/services/T1234567/AAAAAAAA/ZZZZZZ"
    expected = {
        "alerts": [
            {
                "id": "5a4981aa-9653-4bd1-bef5-d6bff52042e4",
                "name": "Landing page degraded performance",
                "type": "latency",
                "threshold": 300,
                "comparison": "greater_than",
                "notifications": {
                    "email": ["bob@example.com"],
                    "slack": [
                        {
                            "channel": "Production Alerts",
                            "url": url,
                        }
                    ],
                },
                "period": "2m",
            }
        ],
        "links": {
            "pages": {
                "pages": {
                    "first": "https://api.digitalocean.com/v2/account/keys?page=1",
                    "prev": "https://api.digitalocean.com/v2/account/keys?page=2",
                }
            }
        },
        "meta": {"total": 1},
    }
    check_id = "4de7ac8b-495b-4884-9a69-1050c6793cd6"
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/uptime/checks/{check_id}/alerts",
        json=expected,
        status=200,
    )

    get_res = mock_client.uptime.list_alerts(check_id)

    assert get_res == expected


@responses.activate
def test_update_alert_put(mock_client: Client, mock_client_url):
    """Mock Uptime Update Alert"""
    url = "https://hooks.slack.com/services/T1234567/AAAAAAAA/ZZZZZZ"
    expected = {
        "alert": {
            "id": "5a4981aa-9653-4bd1-bef5-d6bff52042e4",
            "name": "Landing page degraded performance",
            "type": "latency",
            "threshold": 300,
            "comparison": "greater_than",
            "notifications": {
                "email": ["bob@example.com"],
                "slack": [
                    {
                        "channel": "Production Alerts",
                        "url": url,
                    }
                ],
            },
            "period": "2m",
        }
    }
    check_id = "4de7ac8b-495b-4884-9a69-1050c6793cd6"
    alert_id = "17f0f0ae-b7e5-4ef6-86e3-aa569db58284"
    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/uptime/checks/{check_id}/alerts/{alert_id}",
        json=expected,
        status=200,
    )
    req = {
        "name": "Landing page degraded performance",
        "type": "latency",
        "threshold": 300,
        "comparison": "greater_than",
        "notifications": {
            "email": ["bob@example.com"],
            "slack": [
                {
                    "channel": "Production Alerts",
                    "url": url,
                }
            ],
        },
        "period": "2m",
    }

    put_res = mock_client.uptime.update_alert(check_id, alert_id, body=req)

    assert put_res == expected
