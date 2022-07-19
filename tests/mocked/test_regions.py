"""Mock tests for the Regions API resource"""

import responses

from digitalocean import DigitalOceanClient


@responses.activate
def test_list_regions(mock_client: DigitalOceanClient, mock_client_url):
    """Mocks the regions list operation"""
    expected = {
        "regions": [
            {
                "name": "New York 3",
                "slug": "nyc3",
                "features": [
                    "private_networking",
                    "backups",
                    "ipv6",
                    "metadata",
                    "install_agent",
                    "storage",
                    "image_transfer",
                ],
                "available": True,
                "sizes": [
                    "s-1vcpu-1gb",
                    "s-1vcpu-2gb",
                    "s-1vcpu-3gb",
                    "s-2vcpu-2gb",
                    "s-3vcpu-1gb",
                    "s-2vcpu-4gb",
                    "s-4vcpu-8gb",
                    "s-6vcpu-16gb",
                    "s-8vcpu-32gb",
                    "s-12vcpu-48gb",
                    "s-16vcpu-64gb",
                    "s-20vcpu-96gb",
                    "s-24vcpu-128gb",
                    "s-32vcpu-192g",
                ],
            }
        ],
        "links": {
            "pages": {
                "last": "https://api.digitalocean.com/v2/regions?page=13&per_page=1",
                "next": "https://api.digitalocean.com/v2/regions?page=2&per_page=1",
            }
        },
        "meta": {"total": 1},
    }

    responses.add(responses.GET, f"{mock_client_url}/v2/regions", json=expected)
    list_resp = mock_client.regions.list()

    assert list_resp == expected
