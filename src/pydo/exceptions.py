"""Exceptions"""

# pylint: disable=unused-import
# Importing exceptions this way makes them accessible through this module.
# Therefore, obscuring azure packages from the end user
from azure.core.exceptions import HttpResponseError


class DigitalOceanError(Exception):
    """Base exception for all DigitalOcean API errors."""

    def __init__(self, message: str, status_code: int = None, response=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class AuthenticationError(DigitalOceanError):
    """Raised when authentication fails (401 Unauthorized)."""
    pass


class PermissionDeniedError(DigitalOceanError):
    """Raised when access is forbidden (403 Forbidden)."""
    pass


class ResourceNotFoundError(DigitalOceanError):
    """Raised when a requested resource is not found (404 Not Found)."""
    pass


class RateLimitError(DigitalOceanError):
    """Raised when API rate limit is exceeded (429 Too Many Requests)."""
    pass


class ServerError(DigitalOceanError):
    """Raised when the server encounters an error (5xx status codes)."""
    pass


class ValidationError(DigitalOceanError):
    """Raised when request validation fails (400 Bad Request)."""
    pass


class ConflictError(DigitalOceanError):
    """Raised when there's a conflict with the current state (409 Conflict)."""
    pass


class ServiceUnavailableError(DigitalOceanError):
    """Raised when the service is temporarily unavailable (503 Service Unavailable)."""
    pass
