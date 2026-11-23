# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Option handling and mappings shared by the sync and async Daytona compat clients."""

import enum
from typing import Any, Dict, List, Mapping, Optional, Tuple

from ...errors import SandboxNotImplementedError
from ...types import PAUSED, RUNNING
from .. import _base


class SandboxState(str, enum.Enum):
    """Sandbox states as Daytona names them (``daytona_api_client.SandboxState``)."""

    CREATING = "creating"
    RESTORING = "restoring"
    DESTROYED = "destroyed"
    DESTROYING = "destroying"
    STARTED = "started"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    BUILD_FAILED = "build_failed"
    PENDING_BUILD = "pending_build"
    BUILDING_SNAPSHOT = "building_snapshot"
    UNKNOWN = "unknown"
    PULLING_SNAPSHOT = "pulling_snapshot"
    ARCHIVED = "archived"
    ARCHIVING = "archiving"
    RESIZING = "resizing"
    SNAPSHOTTING = "snapshotting"
    FORKING = "forking"
    PAUSING = "pausing"
    PAUSED = "paused"
    RESUMING = "resuming"


class SnapshotState(str, enum.Enum):
    """Snapshot states as Daytona names them."""

    BUILDING = "building"
    PENDING = "pending"
    PULLING = "pulling"
    SNAPSHOTTING = "snapshotting"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    BUILD_FAILED = "build_failed"
    REMOVING = "removing"


#: ``DaytonaConfig`` fields that only tune the HTTP client: accepted and ignored.
CLIENT_SIDE_CONFIG = (
    "request_timeout",
    "max_response_bytes",
    "connection_pool_maxsize",
    "otel_enabled",
    "shared_hub",
    "use_deprecated_polling",
)

#: ``DaytonaConfig`` fields that name Daytona's servers, regions or accounts.
DAYTONA_ONLY_CONFIG = (
    "api_url",
    "server_url",
    "jwt_token",
    "organization_id",
    "project_id",
    "target",
    "events",
)


def resolve_config(
    qualified: str, config: Any, extras: Mapping[str, Any]
) -> Dict[str, Any]:
    """The DigitalOcean connection a ``DaytonaConfig`` stands for.

    ``config.api_key`` is the DigitalOcean API token. The fields that point at
    Daytona (URL, organization, region, JWT) raise, so a DigitalOcean token is
    never sent to Daytona. ``extras`` carries ``do_api_url`` and ``size``.
    """
    for name in DAYTONA_ONLY_CONFIG:
        if getattr(config, name, None) is not None:
            raise SandboxNotImplementedError(
                "%s(config.%s=...)" % (qualified, name),
                reason="Daytona's servers, organizations and regions are not used; "
                "set DIGITALOCEAN_API_URL for another API origin",
            )
    return {
        "token": getattr(config, "api_key", None),
        "api_url": extras.get("do_api_url"),
        "size": extras.get("size"),
    }


def state_of(do_state: str) -> SandboxState:
    if do_state == RUNNING:
        return SandboxState.STARTED
    if do_state == PAUSED:
        return SandboxState.STOPPED
    return SandboxState.CREATING


def do_state_filter(states: Optional[List[Any]]) -> Optional[str]:
    """The one DigitalOcean state a Daytona ``states`` filter selects, or ``None``."""
    if not states:
        return None
    wanted = {SandboxState(getattr(s, "value", s)) for s in states}
    if wanted == {SandboxState.STARTED}:
        return RUNNING
    if wanted <= {SandboxState.STOPPED, SandboxState.PAUSED}:
        return PAUSED
    if wanted >= {SandboxState.STARTED, SandboxState.STOPPED}:
        return None
    raise SandboxNotImplementedError(
        "Daytona.list(query.states=%s)" % sorted(w.value for w in wanted),
        "sandbox states other than started and stopped",
    )


def reject(qualified: str, needs: str, **given: Any) -> None:
    _base.reject("daytona", qualified, needs, **given)


def create_options(
    qualified: str, params: Any
) -> Tuple[Optional[str], Optional[Dict[str, str]], Optional[bool]]:
    """``(template, env_vars, allow_internet_access)`` from Daytona create params.

    ``snapshot`` names the template. Daytona-only options raise.
    """
    if params is None:
        return None, None, None
    if getattr(params, "image", None) is not None:
        raise SandboxNotImplementedError(
            "%s(params.image=...)" % _base.labelled("daytona", qualified),
            "sandboxes from an image (build a template with snapshot.create(CreateSnapshotParams(name=..., image=...)) and pass its name as snapshot)",
        )
    reject(
        qualified,
        "sandbox naming, labels, lifetime, auto-stop, volumes, secrets, network allow-lists, resources, region and runtime options",
        language=getattr(params, "language", None),
        name=getattr(params, "name", None),
        os_user=getattr(params, "os_user", None),
        labels=getattr(params, "labels", None),
        public=getattr(params, "public", None),
        auto_stop_interval=getattr(params, "auto_stop_interval", None),
        auto_pause_interval=getattr(params, "auto_pause_interval", None),
        auto_archive_interval=getattr(params, "auto_archive_interval", None),
        auto_delete_interval=getattr(params, "auto_delete_interval", None),
        ttl_minutes=getattr(params, "ttl_minutes", None),
        queue_timeout=getattr(params, "queue_timeout", None),
        volumes=getattr(params, "volumes", None),
        secrets=getattr(params, "secrets", None),
        kvm=getattr(params, "kvm", None),
        network_allow_list=getattr(params, "network_allow_list", None),
        domain_allow_list=getattr(params, "domain_allow_list", None),
        outbound_proxy_url=getattr(params, "outbound_proxy_url", None),
        otel_endpoint_override=getattr(params, "otel_endpoint_override", None),
        ephemeral=getattr(params, "ephemeral", None),
        spot=getattr(params, "spot", None),
        linked_sandbox=getattr(params, "linked_sandbox", None),
        target=getattr(params, "target", None),
        resources=getattr(params, "resources", None),
    )
    block = getattr(params, "network_block_all", None)
    allow = None if block is None else (not block)
    return getattr(params, "snapshot", None), getattr(params, "env_vars", None), allow


def snapshot_state(status: str) -> SnapshotState:
    if status == "TEMPLATE_STATUS_READY":
        return SnapshotState.ACTIVE
    if status == "TEMPLATE_STATUS_FAILED":
        return SnapshotState.BUILD_FAILED
    return SnapshotState.BUILDING
