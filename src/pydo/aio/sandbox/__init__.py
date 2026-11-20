# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async DigitalOcean Sandboxes (``/v2/sandboxes``).

Hand-written; preserved across ``make generate``. The async twin of
:mod:`pydo.sandbox`. Errors and types are shared with it.
"""

from pydo.sandbox.errors import (
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
from pydo.sandbox.types import DEFAULT_SIZE, DEFAULT_TEMPLATE, SandboxInfo, SandboxState

from .client import SandboxClient
from .sandbox import Sandbox, SandboxPaginator

__all__ = [
    "AuthenticationError",
    "ConflictError",
    "DEFAULT_SIZE",
    "DEFAULT_TEMPLATE",
    "InvalidRequestError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    "Sandbox",
    "SandboxClient",
    "SandboxError",
    "SandboxInfo",
    "SandboxPaginator",
    "SandboxState",
    "SandboxTimeoutError",
    "ServiceError",
]
