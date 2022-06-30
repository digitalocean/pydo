import pytest

from digitalocean import DigitalOceanClient


@pytest.fixture(scope="module")
def mock_client_url():
    return "https://testing.local"


@pytest.fixture(scope="module")
def mock_client(mock_client_url) -> DigitalOceanClient:
    return DigitalOceanClient("", endpoint=mock_client_url)
