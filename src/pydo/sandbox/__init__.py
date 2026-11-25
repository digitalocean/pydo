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

from ._commands import CommandEvent, CommandInfo, CommandResult
from .client import SandboxClient
from .commands import Command, Commands
from ._files import FileEntry, FileType, MakeDirResult, WriteInfo
from .files import Files
from ._templates import ImageSource, TemplateBuildInfo, TemplateInfo, TemplateStatus
from .templates import Pages, Template
from ._snapshots import SnapshotInfo, SnapshotState
from .snapshots import Snapshot
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
    "Command",
    "CommandEvent",
    "CommandInfo",
    "CommandResult",
    "Commands",
    "FileEntry",
    "FileType",
    "Files",
    "MakeDirResult",
    "WriteInfo",
    "ImageSource",
    "Pages",
    "Snapshot",
    "SnapshotInfo",
    "SnapshotState",
    "Template",
    "TemplateBuildInfo",
    "TemplateInfo",
    "TemplateStatus",
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
