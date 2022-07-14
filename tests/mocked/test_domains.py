"""Mock tests for the domains API resource"""

import responses

from digitalocean import DigitalOceanClient


@responses.activate
def test_create_record(mock_client: DigitalOceanClient, mock_client_url):
    expected = {"domain": {"name": "clienttest.com", "ttl": 1800, "zone_file": ""}}

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/domains",
        json=expected,
        status=201,
    )

    create_resp = mock_client.domains.create({"name": "clienttest.com"})

    assert create_resp == expected
