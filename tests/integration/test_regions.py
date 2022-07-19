""" test_regions.py
    Integration Test for Regions
"""

from digitalocean import DigitalOceanClient


def test_regions(integration_client: DigitalOceanClient):
    """Testing the list of regions"""

    list_resp = integration_client.regions.list()

    assert list_resp is not None
