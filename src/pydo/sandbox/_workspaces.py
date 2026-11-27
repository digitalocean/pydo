# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Types and helpers shared by the sync and async sandbox workspaces.

Hand-written; preserved across ``make generate``.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import quote

from .errors import SandboxError
from .types import _parse_time

#: ``/v2/sandboxes/workspaces``, relative to the API origin.
COLLECTION_PATH = "/v2/sandboxes/workspaces"

#: Workspace state values: ``WORKSPACE_STATE_CREATING``, ``..._AVAILABLE``,
#: ``..._ATTACHING``, ``..._ATTACHED``, ``..._RELEASING``, ``..._DELETING``,
#: ``..._FAILED`` (and ``..._UNSPECIFIED``).
WorkspaceState = str
CREATING = "WORKSPACE_STATE_CREATING"
AVAILABLE = "WORKSPACE_STATE_AVAILABLE"
ATTACHING = "WORKSPACE_STATE_ATTACHING"
ATTACHED = "WORKSPACE_STATE_ATTACHED"
RELEASING = "WORKSPACE_STATE_RELEASING"
DELETING = "WORKSPACE_STATE_DELETING"
FAILED = "WORKSPACE_STATE_FAILED"
UNSPECIFIED = "WORKSPACE_STATE_UNSPECIFIED"


@dataclass
class WorkspaceInfo:
    """A workspace record as the API last returned it."""

    workspace_id: str
    state: WorkspaceState
    size_limit_gib: int
    #: Empty when no name was given.
    name: str = ""
    #: The sandbox the workspace is attached to, if any.
    attached_sandbox_id: Optional[str] = None
    last_saved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


def _time(raw: Any) -> Optional[datetime]:
    return _parse_time(raw) if raw else None


def _int(raw: Any) -> int:
    # uint64 fields such as ``size_limit_gib`` can arrive as JSON strings.
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def to_workspace(raw: Any) -> WorkspaceInfo:
    """Builds a :class:`WorkspaceInfo` from a workspace object."""
    if not isinstance(raw, dict) or not raw.get("workspace_id"):
        raise SandboxError("the API response did not include the workspace")
    return WorkspaceInfo(
        workspace_id=raw["workspace_id"],
        state=raw.get("state") or UNSPECIFIED,
        size_limit_gib=_int(raw.get("size_limit_gib")),
        name=raw.get("name") or "",
        attached_sandbox_id=raw.get("attached_sandbox_id") or None,
        last_saved_at=_time(raw.get("last_saved_at")),
        created_at=_time(raw.get("created_at")),
    )


def create_body(name: Optional[str], size_limit_gib: int) -> Dict[str, Any]:
    """Validates create arguments and builds the request body."""
    if (
        isinstance(size_limit_gib, bool)
        or not isinstance(size_limit_gib, int)
        or size_limit_gib < 1
    ):
        raise SandboxError(
            "Workspace.create: `size_limit_gib` must be a positive integer"
        )
    body: Dict[str, Any] = {"size_limit_gib": size_limit_gib}
    if name is not None and name.strip():
        body["name"] = name
    return body


def require_workspace_id(workspace_id: str) -> str:
    if not workspace_id or not str(workspace_id).strip():
        raise SandboxError("`workspace_id` is required")
    return workspace_id


def item_path(workspace_id: str) -> str:
    """The path of one workspace."""
    return "%s/%s" % (
        COLLECTION_PATH,
        quote(require_workspace_id(workspace_id), safe=""),
    )


def not_available_message(info: WorkspaceInfo) -> Optional[str]:
    """Why a workspace can no longer become available, or ``None`` if it still can."""
    if info.state in (FAILED, DELETING):
        return "workspace %s cannot become available (state %s)" % (
            info.workspace_id,
            info.state,
        )
    return None
