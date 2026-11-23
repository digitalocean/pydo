# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Types and option handling shared by the sync and async E2B compat clients."""

import enum
from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Mapping, Optional, Tuple, TypeVar

from ...errors import SandboxNotImplementedError
from ...types import PAUSED, RUNNING
from .. import _base
from . import _mirror as _m
from .exceptions import SandboxException

OutputT = TypeVar("OutputT")

#: ``ApiParams`` keys that only tune the HTTP client: accepted and ignored.
CLIENT_SIDE_OPTIONS = (
    "request_timeout",
    "retries",
    "headers",
    "api_headers",
    "validate_api_key",
    "debug",
    "proxy",
    "http_version",
)

#: ``ApiParams`` keys that point at E2B's servers: refused, never forwarded.
E2B_URL_OPTIONS = ("domain", "api_url", "sandbox_url")


class SandboxState(str, enum.Enum):
    """State of a sandbox as E2B names it."""

    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class CommandResult(Generic[OutputT]):
    """Result of a command that finished."""

    stderr: OutputT
    stdout: OutputT
    exit_code: int
    error: Optional[str] = None


class CommandExitException(SandboxException):
    """Raised by ``commands.run`` when the command exits with a non-zero code."""

    def __init__(
        self,
        stderr: Optional[str],
        stdout: Optional[str],
        exit_code: int,
        error: Optional[str] = None,
    ) -> None:
        super().__init__(
            "Command exited with code %s" % exit_code
            if stderr is None
            else "Command exited with code %s and error:\n%s" % (exit_code, stderr)
        )
        self.stderr = stderr
        self.stdout = stdout
        self.exit_code = exit_code
        self.error = error

    def __str__(self) -> str:
        return self.args[0]


def connection(
    qualified: str, opts: Mapping[str, Any], defaults: Mapping[str, Any]
) -> Tuple[Optional[str], Optional[str]]:
    """Resolves ``(token, api_url)`` from E2B ``ApiParams`` plus the client defaults.

    ``api_key`` becomes the DigitalOcean token. The options that name E2B's own
    servers raise, so a DigitalOcean token is never sent to them.
    """
    for key in E2B_URL_OPTIONS:
        if opts.get(key) is not None:
            raise SandboxNotImplementedError(
                "E2B.%s(%s=...)" % (qualified, key),
                reason="E2B's servers are not used; set DIGITALOCEAN_API_URL for another API origin",
            )
    token = opts.get("api_key") or defaults.get("token")
    return token, defaults.get("api_url")


def sandbox_info(info: Any) -> Any:
    """An E2B ``SandboxInfo`` from a DigitalOcean :class:`SandboxInfo`."""
    state = SandboxState.RUNNING if info.state == RUNNING else SandboxState.PAUSED
    return _m.SandboxInfo(
        sandbox_id=info.sandbox_id,
        sandbox_domain=None,
        template_id=info.template,
        name=info.template,
        metadata={},
        started_at=info.created_at,
        end_at=None,
        state=state,
        cpu_count=None,
        memory_mb=None,
        envd_version=None,
        allow_internet_access=None,
        network=None,
        lifecycle=None,
        volume_mounts=None,
        envd_unresponsive_at_pause=None,
    )


def process_info(item: Any) -> Any:
    """An E2B ``ProcessInfo`` from a DigitalOcean :class:`CommandInfo`."""
    return _m.ProcessInfo(
        pid=item.pid, tag=None, cmd=item.cmd, args=[], envs={}, cwd=item.cwd
    )


def snapshot_info(snapshot: Any) -> Any:
    """An E2B ``SnapshotInfo`` from a DigitalOcean :class:`Snapshot`."""
    names = [snapshot.name] if snapshot.name else []
    return _m.SnapshotInfo(snapshot_id=snapshot.snapshot_id, names=names)


def state_filter(query: Any) -> Optional[str]:
    """The one DigitalOcean state a list query selects, or ``None`` for any.

    E2B lists ``running`` and ``paused`` sandboxes by default. The API takes one
    state at a time, so both together mean no filter.
    """
    if query is None:
        return None
    for field in ("metadata", "started_after", "template"):
        if getattr(query, field, None):
            raise SandboxNotImplementedError(
                "E2B.Sandbox.list(query.%s=...)" % field,
                "a sandbox metadata, start time, or template filter",
            )
    states = [
        SandboxState(s) if not isinstance(s, SandboxState) else s
        for s in (query.state or [])
    ]
    if not states or set(states) == {SandboxState.RUNNING, SandboxState.PAUSED}:
        return None
    if len(states) == 1:
        return RUNNING if states[0] is SandboxState.RUNNING else PAUSED
    return None


def reject_lifetime(qualified: str, **given: Any) -> None:
    """Refuse sandbox-lifetime and metadata options the API has no field for."""
    _base.reject("e2b", qualified, "a sandbox lifetime API", **given)


def check_pause_options(
    qualified: str, keep_memory: Optional[bool], mode: Optional[str]
) -> None:
    if keep_memory is False:
        raise SandboxNotImplementedError(
            "E2B.%s(keep_memory=False)" % qualified, "a pause without memory option"
        )
    if mode is not None:
        raise SandboxNotImplementedError(
            "E2B.%s(mode=...)" % qualified, "a snapshot mode option"
        )


def no_list_options(order: Optional[str]) -> None:
    if order is not None:
        raise SandboxNotImplementedError(
            "E2B.Sandbox.list(order=...)", "a list order option"
        )


def noop_dict() -> Dict[str, Any]:
    return {}


__all__: List[str] = [
    "CLIENT_SIDE_OPTIONS",
    "CommandExitException",
    "CommandResult",
    "SandboxState",
]
