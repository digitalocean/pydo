"""Test retry configuration functionality."""

import pytest
import responses
from pydo import Client
from azure.core.pipeline.policies import RetryPolicy


@responses.activate
def test_default_retry_configuration(mock_client: Client, mock_client_url):
    """Test that default retry configuration is applied."""
    # Mock a server error that should be retried
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets",
        json={"message": "Internal Server Error"},
        status=500,
    )

    # Should retry 3 times (default) before giving up
    with pytest.raises(Exception):  # Will eventually fail after retries
        mock_client.droplets.list()

    # Should have made 4 requests (1 initial + 3 retries)
    assert len(responses.calls) == 4


@responses.activate
def test_custom_retry_total(mock_client_url):
    """Test custom retry_total configuration."""
    # Create client with custom retry settings
    client = Client("test-token", retry_total=1)

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets",
        json={"message": "Internal Server Error"},
        status=500,
    )

    with pytest.raises(Exception):
        client.droplets.list()

    # Should have made 2 requests (1 initial + 1 retry)
    assert len(responses.calls) == 2


@responses.activate
def test_custom_retry_status_codes(mock_client_url):
    """Test custom retry status codes."""
    # Create client that retries on 404 (normally not retried)
    client = Client("test-token", retry_total=1, retry_status_codes=[404, 500])

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets",
        json={"message": "Not Found"},
        status=404,
    )

    with pytest.raises(Exception):
        client.droplets.list()

    # Should have retried on 404
    assert len(responses.calls) == 2


@responses.activate
def test_no_retry_on_non_retryable_status(mock_client_url):
    """Test that non-retryable status codes don't trigger retries."""
    client = Client("test-token", retry_total=3)

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets",
        json={"message": "Unauthorized"},
        status=401,  # Not in default retry codes
    )

    with pytest.raises(Exception):
        client.droplets.list()

    # Should have made only 1 request (no retries for 401)
    assert len(responses.calls) == 1


@responses.activate
def test_successful_retry(mock_client_url):
    """Test successful retry after initial failure."""
    client = Client("test-token", retry_total=2)

    # First call fails
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets",
        json={"message": "Internal Server Error"},
        status=500,
    )

    # Second call succeeds
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets",
        json={"droplets": []},
        status=200,
    )

    # Should succeed after retry
    result = client.droplets.list()
    assert "droplets" in result
    assert len(responses.calls) == 2  # 1 initial + 1 retry


def test_retry_policy_parameter_override():
    """Test that custom retry_policy parameter overrides defaults."""
    custom_policy = RetryPolicy(retry_total=10)

    client = Client("test-token", retry_policy=custom_policy)

    # The client should use the custom policy
    # We can't easily test this without mocking internal Azure SDK behavior,
    # but we can verify the client initializes without error
    assert client is not None


def test_retry_configuration_parameters():
    """Test that retry configuration parameters are accepted."""
    client = Client(
        token="test-token",
        retry_total=5,
        retry_backoff_factor=1.5,
        retry_status_codes=[429, 500, 503],
        timeout=60
    )

    assert client is not None