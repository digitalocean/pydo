"""Test custom exceptions."""

import pytest
import responses
from pydo import Client
from pydo.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    ConflictError,
    DigitalOceanError
)


@responses.activate
def test_authentication_error(mock_client: Client, mock_client_url):
    """Test AuthenticationError for 401 responses."""
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets",
        json={"message": "Unauthorized"},
        status=401,
    )

    with pytest.raises(AuthenticationError) as exc_info:
        mock_client.droplets.list()

    assert "Authentication failed" in str(exc_info.value)
    assert exc_info.value.status_code == 401


@responses.activate
def test_permission_denied_error(mock_client: Client, mock_client_url):
    """Test PermissionDeniedError for 403 responses."""
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets",
        json={"message": "Forbidden"},
        status=403,
    )

    with pytest.raises(PermissionDeniedError) as exc_info:
        mock_client.droplets.list()

    assert "Access forbidden" in str(exc_info.value)
    assert exc_info.value.status_code == 403


@responses.activate
def test_resource_not_found_error(mock_client: Client, mock_client_url):
    """Test ResourceNotFoundError for 404 responses."""
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets/999999",
        json={"message": "Not Found"},
        status=404,
    )

    with pytest.raises(ResourceNotFoundError) as exc_info:
        mock_client.droplets.get(droplet_id=999999)

    assert "Resource not found" in str(exc_info.value)
    assert exc_info.value.status_code == 404


@responses.activate
def test_validation_error(mock_client: Client, mock_client_url):
    """Test ValidationError for 400 responses."""
    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/droplets",
        json={"message": "Bad Request"},
        status=400,
    )

    with pytest.raises(ValidationError) as exc_info:
        mock_client.droplets.create({})

    assert "Bad request" in str(exc_info.value)
    assert exc_info.value.status_code == 400


@responses.activate
def test_rate_limit_error(mock_client: Client, mock_client_url):
    """Test RateLimitError for 429 responses."""
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets",
        json={"message": "Too Many Requests"},
        status=429,
    )

    with pytest.raises(RateLimitError) as exc_info:
        mock_client.droplets.list()

    assert "Rate limit exceeded" in str(exc_info.value)
    assert exc_info.value.status_code == 429


@responses.activate
def test_server_error(mock_client: Client, mock_client_url):
    """Test ServerError for 5xx responses."""
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets",
        json={"message": "Internal Server Error"},
        status=500,
    )

    with pytest.raises(ServerError) as exc_info:
        mock_client.droplets.list()

    assert "Server error" in str(exc_info.value)
    assert exc_info.value.status_code == 500


@responses.activate
def test_service_unavailable_error(mock_client: Client, mock_client_url):
    """Test ServiceUnavailableError for 503 responses."""
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/droplets",
        json={"message": "Service Unavailable"},
        status=503,
    )

    with pytest.raises(ServiceUnavailableError) as exc_info:
        mock_client.droplets.list()

    assert "Service temporarily unavailable" in str(exc_info.value)
    assert exc_info.value.status_code == 503


@responses.activate
def test_conflict_error(mock_client: Client, mock_client_url):
    """Test ConflictError for 409 responses."""
    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/droplets",
        json={"message": "Conflict"},
        status=409,
    )

    with pytest.raises(ConflictError) as exc_info:
        mock_client.droplets.create({})

    assert "Conflict" in str(exc_info.value)
    assert exc_info.value.status_code == 409


def test_exception_inheritance():
    """Test that custom exceptions inherit from DigitalOceanError."""
    auth_error = AuthenticationError("test")
    assert isinstance(auth_error, DigitalOceanError)

    not_found_error = ResourceNotFoundError("test")
    assert isinstance(not_found_error, DigitalOceanError)

    rate_limit_error = RateLimitError("test")
    assert isinstance(rate_limit_error, DigitalOceanError)


def test_exception_attributes():
    """Test that exceptions store status_code and response properly."""
    error = AuthenticationError("test message", status_code=401, response="test_response")
    assert error.message == "test message"
    assert error.status_code == 401
    assert error.response == "test_response"