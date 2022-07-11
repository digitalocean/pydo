"""Mock tests for the domains API resource"""

import responses

from digitalocean import DigitalOceanClient


@responses.activate
def test_create_record(mock_client: DigitalOceanClient):
    pass
