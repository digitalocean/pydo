""" test_cdn.py
    Integration tests for CDN
"""

from tests.integration import defaults
from tests.integration import shared
from digitalocean import Client


def test_cdn_lifecycle(integration_client: Client, public_key: bytes):
    """Tests the complete lifecycle of a CDN
    Creates, Lists, Gets, Updates, Deletes, Purges.
    """
