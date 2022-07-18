# pylint: disable=redefined-outer-name
"""Pytest configuration for mocked tests."""
import pytest

from digitalocean import GeneratedClient


@pytest.fixture(scope="module")
def mock_client_url():
    """Returns a url used as the API endpoint for the mock client."""
    return "https://testing.local"


@pytest.fixture(scope="module")
def mock_client(mock_client_url) -> GeneratedClient:
    """Initializes a mock client
    The mock client doesn't use a valid token and has a fake API endpoint set.
    """
    return GeneratedClient("", endpoint=mock_client_url)
