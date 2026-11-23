# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""The Modal exception hierarchy (modal 1.6.4), raised by the compat client.

Hand-written; preserved across ``make generate``. The names and bases match
``modal.exception`` (without the gRPC wrapper base), so ``except modal.exception
.NotFoundError`` keeps working. Each exception raised for a failed DigitalOcean
call chains the SDK's own typed error as ``__cause__``.
"""

from ... import errors as _e


class Error(Exception):
    """Base class for Modal errors."""


class AlreadyExistsError(Error):
    """The object already exists."""


class AuthError(Error):
    """The token is missing or invalid."""


class InternalError(Error):
    """An internal server error."""


class InvalidError(Error):
    """The request is invalid."""


class ConflictError(InvalidError):
    """The state conflicts with the request."""


class NotFoundError(Error):
    """The object was not found."""


class PermissionDeniedError(Error):
    """The token does not allow the operation."""


class ResourceExhaustedError(Error):
    """A quota or rate limit was exceeded."""


class ServiceError(Error):
    """The service failed."""


class RemoteError(Error):
    """A remote execution error."""


class TimeoutError(Error):  # pylint: disable=redefined-builtin
    """A wait timed out."""


class SandboxTimeoutError(TimeoutError):
    """The sandbox timed out."""


class ExecTimeoutError(TimeoutError):
    """An exec timed out."""


class SandboxTerminatedError(Error):
    """The sandbox was terminated."""


class SnapshotCreationError(Error):
    """A snapshot could not be created."""


class ExecutionError(Error):
    """An execution error."""


class ConnectionError(Error):  # pylint: disable=redefined-builtin
    """The connection failed."""


class VersionError(Error):
    """The client version is not supported."""


class SandboxFilesystemError(Error):
    """A sandbox filesystem error."""


class ImageBuildError(RemoteError):
    """An image build failed."""


def map_error(err: _e.SandboxError) -> BaseException:
    """The Modal exception for a failed Sandboxes SDK call."""
    message = str(err)
    for sdk_error, modal_error in (
        (_e.AuthenticationError, AuthError),
        (_e.NotFoundError, NotFoundError),
        (_e.PermissionDeniedError, PermissionDeniedError),
        (_e.ConflictError, ConflictError),
        (_e.InvalidRequestError, InvalidError),
        (_e.RateLimitError, ResourceExhaustedError),
        (_e.SandboxTimeoutError, TimeoutError),
        (_e.ServiceError, ServiceError),
    ):
        if isinstance(err, sdk_error):
            return modal_error(message)
    return Error(message)
