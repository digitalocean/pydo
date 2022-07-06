# pylint: disable=redefined-outer-name
"""Pytest configuration for mocked tests."""
import pytest

from digitalocean import DigitalOceanClient


@pytest.fixture(scope="module")
def mock_client_url():
    """Returns a url used as the API endpoint for the mock client."""
    return "https://testing.local"


@pytest.fixture(scope="module")
def mock_client(mock_client_url) -> DigitalOceanClient:
    """Initializes a mock client
    The mock client doesn't use a valid token and has a fake API endpoint set.
    """
    return DigitalOceanClient("", endpoint=mock_client_url)
