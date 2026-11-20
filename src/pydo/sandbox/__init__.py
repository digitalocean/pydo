# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""DigitalOcean Sandboxes (``/v2/sandboxes``).

Hand-written; preserved across ``make generate``. Not imported by ``import pydo``:
import it where you use it.

.. code-block:: python

    from pydo.sandbox import Sandbox

    sandbox = Sandbox.create(template="coding-base")
    sandbox.pause()
    sandbox.resume()
    sandbox.kill()

The async twin is :mod:`pydo.aio.sandbox`.
"""

from .client import SandboxClient
from .errors import (
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
from .sandbox import Sandbox, SandboxPaginator
from .types import DEFAULT_SIZE, DEFAULT_TEMPLATE, SandboxInfo, SandboxState

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
