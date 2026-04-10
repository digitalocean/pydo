"""Exceptions"""

# pylint: disable=unused-import
# Importing exceptions this way makes them accessible through this module.
# Therefore, obscuring azure packages from the end user
from azure.core.exceptions import HttpResponseError


class SSEStreamTransportError(RuntimeError):
    """Raised when reading an SSE stream fails before a clean end.

    Typical causes: dropped connections, timeouts, incomplete lines at EOF.
    """


class SSEStreamDecodeError(ValueError):
    """Raised when a complete ``data:`` line is not valid JSON."""


class SSEStreamRetryExhaustedError(RuntimeError):
    """Raised when all retry attempts for an SSE stream have failed."""
