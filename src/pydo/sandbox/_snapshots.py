# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Types and helpers shared by the sync and async sandbox snapshots.

Hand-written; preserved across ``make generate``.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from .errors import SandboxError
from .types import _parse_time

#: Snapshot state values: ``SNAPSHOT_STATE_CREATING``, ``..._UPLOADING``,
#: ``..._COMPLETE``, ``..._FAILED`` (and ``..._UNSPECIFIED``).
SnapshotState = str
COMPLETE = "SNAPSHOT_STATE_COMPLETE"
FAILED = "SNAPSHOT_STATE_FAILED"

_NAME = re.compile(r"^[a-z0-9-]{1,63}$")


@dataclass
class SnapshotInfo:
    """A snapshot record as the API last returned it."""

    snapshot_id: str
    sandbox_id: str
    state: SnapshotState
    #: The name given at creation, if any.
    name: Optional[str] = None
    #: Size in bytes. Set when the snapshot is complete.
    size_bytes: Optional[int] = None
    created_at: Optional[datetime] = None
    #: Why the snapshot failed. Set when the state is failed.
    error_message: Optional[str] = None
    #: How long the snapshot is kept, such as ``168h``. ``None`` when the platform default applies.
    ttl: Optional[str] = None


def _size(raw: Any) -> Optional[int]:
    try:
        return int(raw) if raw not in (None, "") else None
    except (TypeError, ValueError):
        return None


def to_snapshot(raw: Any) -> SnapshotInfo:
    """Builds a :class:`SnapshotInfo` from a snapshot object."""
    if not isinstance(raw, dict) or not raw.get("snapshot_id"):
        raise SandboxError("the API response did not include the snapshot")
    created = raw.get("created_at")
    return SnapshotInfo(
        snapshot_id=raw["snapshot_id"],
        sandbox_id=raw.get("sandbox_id") or "",
        state=raw.get("state") or "SNAPSHOT_STATE_UNSPECIFIED",
        name=raw.get("name") or None,
        size_bytes=_size(raw.get("size_bytes")),
        created_at=_parse_time(created) if created else None,
        error_message=raw.get("error_message") or None,
        ttl=raw.get("ttl") or None,
    )


def create_body(name: Optional[str], ttl: Optional[str]) -> Optional[Dict[str, Any]]:
    """Validates create arguments and builds the request body.

    Returns ``None`` when there is nothing to send: the body is optional.
    """
    body: Dict[str, Any] = {}
    if name is not None:
        if not _NAME.match(str(name)):
            raise SandboxError(
                "snapshot `name` must be 1 to 63 characters: lowercase letters, "
                "digits and hyphens"
            )
        body["name"] = name
    if ttl is not None:
        if not isinstance(ttl, str) or not ttl.strip():
            raise SandboxError("snapshot `ttl` must be a duration string, such as 168h")
        body["ttl"] = ttl
    return body or None


def require_snapshot_id(snapshot_id: str) -> str:
    if not snapshot_id or not str(snapshot_id).strip():
        raise SandboxError("`snapshot_id` is required")
    return snapshot_id


def failure_message(snapshot: SnapshotInfo) -> str:
    """Explains a failed snapshot with the API's error message."""
    message = "snapshot %s failed" % snapshot.snapshot_id
    return (
        "%s: %s" % (message, snapshot.error_message)
        if snapshot.error_message
        else message
    )
