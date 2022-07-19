# pylint: disable=duplicate-code
"""Mock tests for the Sizes API resource"""

import responses

from digitalocean import DigitalOceanClient


@responses.activate
def test_list_sizes(mock_client: DigitalOceanClient, mock_client_url):
    """Mock the sizes list operation"""
    expected = {
        "sizes": [
            {
                "slug": "s-1vcpu-1gb",
                "memory": 1024,
                "vcpus": 1,
                "disk": 25,
                "transfer": 1,
                "price_monthly": 5,
                "price_hourly": 0.00743999984115362,
                "regions": [
                    "ams2",
                    "ams3",
                    "blr1",
                    "fra1",
                    "lon1",
                    "nyc1",
                    "nyc2",
                    "nyc3",
                    "sfo1",
                    "sfo2",
                    "sfo3",
                    "sgp1",
                    "tor1",
                ],
                "available": True,
                "description": "Basic",
            }
        ],
        "links": {
            "pages": {
                "last": "https://api.digitalocean.com/v2/sizes?page=64&per_page=1",
                "next": "https://api.digitalocean.com/v2/sizes?page=2&per_page=1",
            }
        },
        "meta": {"total": 64},
    }
    responses.add(responses.GET, f"{mock_client_url}/v2/sizes", json=expected)
    list_resp = mock_client.sizes.list()

    assert list_resp == expected
