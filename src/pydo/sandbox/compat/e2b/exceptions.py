# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""The E2B exception hierarchy (e2b 2.64.0), raised by the compat client.

Hand-written; preserved across ``make generate``. The class names and bases
match ``e2b.exceptions`` so ``except e2b.NotFoundException`` keeps working. Each
exception raised for a failed DigitalOcean call chains the SDK's own typed error
as ``__cause__``.
"""

from typing import Optional

from ...errors import (
    AuthenticationError,
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    SandboxError,
    SandboxTimeoutError,
)


class SandboxException(Exception):
    """Base class for E2B sandbox errors."""

    def __init__(self, *args, status_code: Optional[int] = None):
        super().__init__(*args)
        self.status_code = status_code


class TimeoutException(SandboxException):
    """A request or wait timed out."""


class InvalidArgumentException(SandboxException):
    """An argument is invalid."""


class NotEnoughSpaceException(SandboxException):
    """The sandbox ran out of space."""


class NotFoundException(SandboxException):
    """A resource was not found."""


class FileNotFoundException(NotFoundException):
    """A file or directory was not found."""


class SandboxNotFoundException(NotFoundException):
    """The sandbox was not found."""


class SandboxNotRunningException(TimeoutException):
    """The sandbox is not running."""


class SandboxUnreachableException(TimeoutException):
    """The sandbox cannot be reached."""


class AuthenticationException(Exception):
    """The API key is missing or invalid."""


class GitAuthException(AuthenticationException):
    """Git authentication failed."""


class GitUpstreamException(SandboxException):
    """The git upstream is not set."""


class TemplateException(SandboxException):
    """A template error."""


class RateLimitException(SandboxException):
    """Too many requests."""

    def __init__(self, *args, status_code: Optional[int] = 429):
        super().__init__(*args, status_code=status_code)


class GuestUnresponsiveException(SandboxException):
    """The guest agent does not respond."""


class ServiceBusyException(Exception):
    """The service is busy."""


class BuildException(Exception):
    """A template build failed."""


class FileUploadException(BuildException):
    """A file upload during a build failed."""


class VolumeException(Exception):
    """A volume error."""


class VolumeNotFoundException(NotFoundException):
    """The volume was not found."""


class VolumePathNotFoundException(NotFoundException):
    """A path in the volume was not found."""


class SecretException(Exception):
    """A secret error."""


class SecretNotFoundException(SecretException):
    """The secret was not found."""


def map_error(err: SandboxError) -> BaseException:
    """The E2B exception for a failed Sandboxes SDK call."""
    message = str(err)
    status = getattr(err, "status", None) or None
    if isinstance(err, AuthenticationError):
        return AuthenticationException(message)
    if isinstance(err, NotFoundError):
        return SandboxNotFoundException(message, status_code=status)
    if isinstance(err, InvalidRequestError):
        return InvalidArgumentException(message, status_code=status)
    if isinstance(err, RateLimitError):
        return RateLimitException(message, status_code=status)
    if isinstance(err, SandboxTimeoutError):
        return TimeoutException(message, status_code=status)
    if isinstance(err, (PermissionDeniedError, ConflictError)):
        return SandboxException(message, status_code=status)
    return SandboxException(message, status_code=status)
