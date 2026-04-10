# pylint: disable=redefined-outer-name
"""Pytest configuration for mocked tests."""
import pytest

from pydo import Client
from pydo.aio import Client as aioClient


@pytest.fixture(scope="module")
def mock_client_url():
    """Returns a url used as the API endpoint for the mock client."""
    return "https://testing.local"


@pytest.fixture(scope="module")
def mock_client(mock_client_url) -> Client:
    """Initializes a mock client
    The mock client doesn't use a valid token and has a fake API endpoint set.
    """
    return Client("", endpoint=mock_client_url)


@pytest.fixture(scope="module")
def mock_aio_client(mock_client_url) -> aioClient:
    """Initializes a mock aio client
    The mock client doesn't use a valid token and has a fake API endpoint set.
    """
    return aioClient("", endpoint=mock_client_url)
