# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Types and helpers shared by the sync and async sandbox files.

Hand-written; preserved across ``make generate``.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Union

from .errors import SandboxError
from .types import _parse_time

#: ``"file"``, ``"directory"``, ``"symlink"`` or ``"unspecified"``.
FileType = str

_TYPES = {
    "FILE_ENTRY_TYPE_FILE": "file",
    "FILE_ENTRY_TYPE_DIRECTORY": "directory",
    "FILE_ENTRY_TYPE_SYMLINK": "symlink",
}

#: The download body ends with ``DOWSSHA1``, the hex SHA-256 of the payload and a newline.
FOOTER_MAGIC = b"DOWSSHA1"
FOOTER_SIZE = len(FOOTER_MAGIC) + 64 + 1
_HEX = re.compile(rb"^[0-9a-f]{64}$")

#: Waits before each retry of an upload or download answered ``503``.
RETRY_DELAYS = (0.5, 1.0, 2.0)


@dataclass(frozen=True)
class FileEntry:
    """A file, directory or symlink in the sandbox."""

    name: str
    type: FileType
    #: The absolute path in the sandbox.
    path: str
    #: Size in bytes.
    size: int = 0
    #: Unix mode bits, such as ``420`` (``0o644``).
    mode: int = 0
    #: The permissions in ``ls`` form, such as ``-rw-r--r--``.
    permissions: str = ""
    owner: str = ""
    group: str = ""
    modified_time: Optional[datetime] = None
    #: Where a symlink points. ``None`` for anything else.
    symlink_target: Optional[str] = None


@dataclass(frozen=True)
class WriteInfo:
    """The outcome of an upload."""

    #: The absolute path written to (the directory, for an archive).
    path: str
    bytes_written: int


@dataclass(frozen=True)
class MakeDirResult:
    """The outcome of :meth:`Files.make_dir`."""

    #: ``False`` when the directory already existed.
    created: bool
    entry: FileEntry


def _int(raw: Any) -> int:
    try:
        return int(raw) if raw not in (None, "") else 0
    except (TypeError, ValueError):
        return 0


def to_entry(raw: Any) -> FileEntry:
    """Builds a :class:`FileEntry` from a file entry object."""
    if not isinstance(raw, dict) or not raw.get("path"):
        raise SandboxError("the API response did not include the file entry")
    modified = raw.get("modified_time")
    return FileEntry(
        name=raw.get("name") or "",
        type=_TYPES.get(raw.get("type") or "", "unspecified"),
        path=raw["path"],
        size=_int(raw.get("size")),
        mode=_int(raw.get("mode")),
        permissions=raw.get("permissions") or "",
        owner=raw.get("owner") or "",
        group=raw.get("group") or "",
        modified_time=_parse_time(modified) if modified else None,
        symlink_target=raw.get("symlink_target") or None,
    )


def to_write_info(raw: Any) -> WriteInfo:
    """Builds a :class:`WriteInfo` from the upload response."""
    if not isinstance(raw, dict):
        raise SandboxError("the API response did not include the upload result")
    return WriteInfo(
        path=raw.get("path") or "", bytes_written=_int(raw.get("bytes_written"))
    )


def to_make_dir(raw: Any) -> MakeDirResult:
    """Builds a :class:`MakeDirResult`. ``created`` is omitted from the body when false."""
    raw = raw if isinstance(raw, dict) else {}
    return MakeDirResult(
        created=bool(raw.get("created")), entry=to_entry(raw.get("entry"))
    )


def require_path(path: str, name: str = "path") -> str:
    if not isinstance(path, str) or not path.strip():
        raise SandboxError("`%s` is required" % name)
    return path


def require_depth(depth: Optional[int]) -> Optional[int]:
    if depth is None:
        return None
    if isinstance(depth, bool) or not isinstance(depth, int) or depth < 0:
        raise SandboxError("`depth` must be a non-negative integer")
    return depth


def to_bytes(data: Union[str, bytes]) -> bytes:
    """Encodes the upload body: ``str`` as UTF-8, bytes-like as is."""
    if isinstance(data, str):
        return data.encode("utf-8")
    if isinstance(data, (bytes, bytearray, memoryview)):
        return bytes(data)
    raise SandboxError("`data` must be str or bytes")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def split_download(body: bytes) -> bytes:
    """Strips the integrity footer from a download body and checks the payload.

    Raises :class:`SandboxError` when the footer is missing or malformed, or
    when the payload does not match its SHA-256.
    """
    if len(body) < FOOTER_SIZE:
        raise SandboxError(
            "the download is missing its integrity footer (%d bytes received)"
            % len(body)
        )
    payload, footer = body[:-FOOTER_SIZE], body[-FOOTER_SIZE:]
    magic, digest, newline = footer[:8], footer[8:72], footer[72:]
    if magic != FOOTER_MAGIC or newline != b"\n" or not _HEX.match(digest):
        raise SandboxError("the download is missing its integrity footer")
    actual = sha256_hex(payload)
    if actual != digest.decode("ascii"):
        raise SandboxError(
            "the download failed its integrity check: SHA-256 %s, footer says %s"
            % (actual, digest.decode("ascii"))
        )
    return payload


def retry_delay(attempt: int, err: SandboxError) -> Optional[float]:
    """Seconds to wait before retrying a ``503``, or ``None`` to give up.

    ``attempt`` counts from 0. ``Retry-After`` wins over the default backoff.
    """
    if err.status != 503 or attempt >= len(RETRY_DELAYS):
        return None
    if err.retry_after is not None:
        return float(err.retry_after)
    return RETRY_DELAYS[attempt]
