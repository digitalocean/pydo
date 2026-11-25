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
    CommandError,
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    SandboxError,
    SandboxTimeoutError,
    ServiceError,
)
from pydo.sandbox._commands import CommandEvent, CommandInfo, CommandResult
from pydo.sandbox.types import DEFAULT_SIZE, DEFAULT_TEMPLATE, SandboxInfo, SandboxState

from .client import SandboxClient
from .commands import Command, Commands
from pydo.sandbox._exec import ExecEvent, ExecResult
from .exec import Exec, ExecSession
from pydo.sandbox._files import FileEntry, FileType, MakeDirResult, WriteInfo
from .files import Files
from pydo.sandbox._templates import (
    ImageSource,
    TemplateBuildInfo,
    TemplateInfo,
    TemplateStatus,
)
from pydo.sandbox._snapshots import SnapshotInfo, SnapshotState
from .snapshots import Snapshot
from .templates import Pages, Template
from .sandbox import Sandbox, SandboxPaginator

__all__ = [
    "AuthenticationError",
    "Command",
    "CommandEvent",
    "CommandInfo",
    "CommandResult",
    "Commands",
    "Exec",
    "ExecEvent",
    "ExecResult",
    "ExecSession",
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
    "CommandError",
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
