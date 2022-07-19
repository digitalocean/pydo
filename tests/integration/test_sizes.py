""" test_sizes.py
    Integration Test for Sizes
"""

from digitalocean import DigitalOceanClient


def test_sizes_list(integration_client: DigitalOceanClient):
    """Testing the List of the Sizes endpoint"""
    list_resp = integration_client.sizes.list()

    assert len(list_resp["sizes"]) >= 20
