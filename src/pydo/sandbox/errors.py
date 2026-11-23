# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Typed errors for the Sandbox SDK.

Hand-written; preserved across ``make generate``. Every failed API call
surfaces as a :class:`SandboxError` subclass chosen by HTTP status, so callers
can branch on the type instead of reading status codes.
"""

from typing import Any, Optional

from azure.core.exceptions import HttpResponseError


class SandboxError(Exception):
    """Any failed sandbox call."""

    def __init__(
        self,
        message: str,
        *,
        status: int = 0,
        code: Optional[str] = None,
        request_id: Optional[str] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        #: HTTP status, or 0 when the failure happened before a response.
        self.status = status
        #: Short stable error id from the API body, such as ``not_found``.
        self.code = code
        #: ``request_id`` from the error body, for support.
        self.request_id = request_id
        #: ``Retry-After`` in seconds, when the server sent one.
        self.retry_after = retry_after


class AuthenticationError(SandboxError):
    """No token, or 401."""


class PermissionDeniedError(SandboxError):
    """403: the token lacks the ``sandbox:*`` scope, or the feature is not enabled."""


class NotFoundError(SandboxError):
    """404: the sandbox or template does not exist, or belongs to another team."""


class InvalidRequestError(SandboxError):
    """400 or 422: malformed request, or the sandbox cannot take it in its current state."""


class ConflictError(SandboxError):
    """409: the sandbox state conflicts with the request."""


class RateLimitError(SandboxError):
    """429: see ``retry_after``."""


class ServiceError(SandboxError):
    """5xx: the service failed. Usually worth retrying."""


class SandboxTimeoutError(SandboxError):
    """A wait ran out of time. The operation may still finish later."""


class SandboxNotImplementedError(SandboxError, NotImplementedError):
    """The call is valid for another sandbox platform but has no DigitalOcean Sandboxes API yet.

    Raised by the migration-only compat clients (``pydo.sandbox.compat``) for
    methods that keep a platform's signature but that the Sandboxes API cannot
    serve, such as file transfer. It is also a :class:`NotImplementedError`.
    """

    def __init__(
        self, feature: str, needs: Optional[str] = None, *, reason: Optional[str] = None
    ) -> None:
        if reason:
            # An option that points at another platform's servers or accounts:
            # not a gap in the API, so it will not be wired up later.
            msg = "%s is not supported on DigitalOcean Sandboxes: %s" % (
                feature,
                reason,
            )
        else:
            msg = "%s is not implemented on DigitalOcean Sandboxes yet" % feature
            if needs:
                msg += ": needs %s" % needs
        super().__init__(msg)
        #: The platform call that was attempted, such as ``E2B.Filesystem.read``.
        self.feature = feature
        #: The missing DigitalOcean Sandboxes capability.
        self.needs = needs
        #: Set when the option has no DigitalOcean counterpart at all.
        self.reason = reason


_BY_STATUS = {
    400: InvalidRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    422: InvalidRequestError,
    429: RateLimitError,
}


def build_error(
    status: int, body: Any, message: Optional[str] = None, headers: Any = None
) -> SandboxError:
    """Builds the typed error for a status and its ``{id, message, request_id}`` body."""
    if not isinstance(body, dict):
        body = {}
    retry_after = None
    if headers is not None:
        raw = headers.get("Retry-After")
        if raw is not None and str(raw).isdigit():
            retry_after = int(raw)
    cls = _BY_STATUS.get(status) or (ServiceError if status >= 500 else SandboxError)
    return cls(
        body.get("message") or message or "HTTP %s" % status,
        status=status,
        code=body.get("id"),
        request_id=body.get("request_id"),
        retry_after=retry_after,
    )


def to_sandbox_error(err: HttpResponseError) -> SandboxError:
    """Converts what the generated client raises into a typed error."""
    response = getattr(err, "response", None)
    try:
        body = response.json() if response is not None else None
    except Exception:  # pylint: disable=broad-except
        body = None
    return build_error(
        getattr(err, "status_code", None) or 0,
        body,
        getattr(err, "message", None),
        getattr(response, "headers", None),
    )


def with_response(pipeline_response: Any, deserialized: Any, _headers: Any) -> Any:
    """``cls`` callback for generated operations: keeps the status with the body.

    The generated operations return an error response's body as a normal result
    for any status the spec lists without ``x-ms-error-response``. Reading the
    status here makes failures raise whatever the spec says.
    """
    response = pipeline_response.http_response
    return response.status_code, deserialized, response.headers


def unwrap(result: Any) -> Any:
    """Returns the body of a :func:`with_response` result, or raises the typed error."""
    status, body, headers = result
    if status >= 400:
        raise build_error(status, body, None, headers)
    return body
