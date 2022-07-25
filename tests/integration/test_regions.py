""" test_regions.py
    Integration Test for Regions
"""

from digitalocean import Client


def test_regions(integration_client: Client):
    """Testing the list of regions"""

    list_resp = integration_client.regions.list()

    assert len(list_resp["regions"]) >= 13
