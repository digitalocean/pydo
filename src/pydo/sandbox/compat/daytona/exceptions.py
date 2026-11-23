# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""The Daytona error hierarchy (daytona 2.1.0), raised by the compat client.

Hand-written; preserved across ``make generate``. The names and bases match
``daytona``'s shared error markers, so ``except daytona.DaytonaNotFoundError``
keeps working. Each exception raised for a failed DigitalOcean call chains the
SDK's own typed error as ``__cause__``.
"""

from typing import Any, Optional

from ...errors import (
    AuthenticationError,
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    SandboxError,
    SandboxTimeoutError,
    ServiceError,
)


class DaytonaError(Exception):
    """Base of every error the SDK raises."""

    def __init__(
        self,
        message: str = "",
        status_code: Optional[int] = None,
        headers: Any = None,
        code: Optional[str] = None,
        source: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.headers = headers
        self.code = code
        self.source = source


class DaytonaBadRequestError(DaytonaError):
    """HTTP 400 and client-side validation."""


class DaytonaAuthenticationError(DaytonaError):
    """Missing or invalid credentials (HTTP 401)."""


class DaytonaForbiddenError(DaytonaError):
    """The credentials do not allow the operation (HTTP 403)."""


class DaytonaNotFoundError(DaytonaError):
    """The resource does not exist (HTTP 404)."""


class DaytonaTimeoutError(DaytonaError):
    """A request or wait timed out."""


class DaytonaConflictError(DaytonaError):
    """The resource's state does not allow the operation (HTTP 409)."""


class DaytonaGoneError(DaytonaError):
    """The resource is gone for good (HTTP 410)."""


class DaytonaUnprocessableEntityError(DaytonaError):
    """The request could not be processed (HTTP 422)."""


class DaytonaRateLimitError(DaytonaError):
    """Too many requests (HTTP 429)."""


class DaytonaInternalServerError(DaytonaError):
    """The server failed (HTTP 500)."""


class DaytonaServiceUnavailableError(DaytonaError):
    """The service is unavailable (HTTP 503)."""


class DaytonaConnectionError(DaytonaError):
    """The connection failed."""


def map_error(err: SandboxError) -> BaseException:
    """The Daytona exception for a failed Sandboxes SDK call."""
    message = str(err)
    status = getattr(err, "status", None) or None
    code = getattr(err, "code", None)
    kind = DaytonaError
    if isinstance(err, AuthenticationError):
        kind = DaytonaAuthenticationError
    elif isinstance(err, PermissionDeniedError):
        kind = DaytonaForbiddenError
    elif isinstance(err, NotFoundError):
        kind = DaytonaNotFoundError
    elif isinstance(err, ConflictError):
        kind = DaytonaConflictError
    elif isinstance(err, RateLimitError):
        kind = DaytonaRateLimitError
    elif isinstance(err, SandboxTimeoutError):
        kind = DaytonaTimeoutError
    elif isinstance(err, InvalidRequestError):
        kind = (
            DaytonaUnprocessableEntityError if status == 422 else DaytonaBadRequestError
        )
    elif isinstance(err, ServiceError):
        kind = DaytonaInternalServerError
    return kind(message, status_code=status, code=code, source="digitalocean-sandboxes")
