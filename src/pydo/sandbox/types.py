# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Types shared by the sync and async Sandbox SDK."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional

from .errors import SandboxError

#: ``SANDBOX_STATE_UNSPECIFIED``, ``SANDBOX_STATE_RUNNING``,
#: ``SANDBOX_STATE_PAUSED`` or ``SANDBOX_STATE_CREATING``.
SandboxState = str

RUNNING = "SANDBOX_STATE_RUNNING"
PAUSED = "SANDBOX_STATE_PAUSED"
CREATING = "SANDBOX_STATE_CREATING"

#: Template used when ``template`` is omitted.
DEFAULT_TEMPLATE = "coding-base"

#: ``size_slug`` used when ``size`` is omitted. It must be an enabled size.
DEFAULT_SIZE = "mars-2vcpu-4gb"


@dataclass
class SandboxInfo:
    """A sandbox record as the API last returned it."""

    sandbox_id: str
    template: str
    state: SandboxState
    size_slug: Optional[str] = None
    created_at: Optional[datetime] = None


def to_info(body: Any) -> SandboxInfo:
    """Builds a :class:`SandboxInfo` from the ``{"sandbox": {...}}`` response."""
    raw: Optional[Mapping[str, Any]] = (
        body.get("sandbox") if isinstance(body, dict) else None
    )
    if not raw or not raw.get("sandbox_id"):
        raise SandboxError("the API response did not include the sandbox")
    created = raw.get("created_at")
    return SandboxInfo(
        sandbox_id=raw["sandbox_id"],
        template=raw.get("template") or "",
        state=raw.get("state") or "SANDBOX_STATE_UNSPECIFIED",
        size_slug=raw.get("size_slug"),
        created_at=_parse_time(created) if created else None,
    )


def _parse_time(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def create_body(
    template: Optional[str],
    size: Optional[str],
    allow_internet_access: Optional[bool],
    env_vars: Optional[Mapping[str, str]],
    workspace_id: Optional[str] = None,
) -> dict:
    """Validates create arguments and builds the request body."""
    if template is None:
        template = DEFAULT_TEMPLATE
    if not str(template).strip():
        raise SandboxError("Sandbox.create: `template` must not be empty")
    body: dict = {"template": template, "size_slug": size or DEFAULT_SIZE}
    if allow_internet_access is not None:
        body["allow_internet_access"] = allow_internet_access
    if env_vars:
        body["env_vars"] = dict(env_vars)
    if workspace_id is not None:
        if not str(workspace_id).strip():
            raise SandboxError("Sandbox.create: `workspace_id` must not be empty")
        body["workspace_id"] = workspace_id
    return body


def require_id(sandbox_id: str) -> str:
    if not sandbox_id or not str(sandbox_id).strip():
        raise SandboxError("`sandbox_id` is required")
    return sandbox_id
