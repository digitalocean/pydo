# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Daytona's ``v0`` namespace (daytona 2.1.0) over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. ``Daytona().create(params)``,
``get``, ``list``, ``start``, ``stop``, ``delete``, ``sandbox.process.exec`` and
snapshots work. Files, git, LSP, code interpreter, computer use, volumes, labels,
preview links and most sandbox settings keep Daytona's signature and raise
:class:`~pydo.sandbox.errors.SandboxNotImplementedError`.

A Daytona *snapshot* (``daytona.snapshot``) is a prebuilt environment, so it maps
to a DigitalOcean *template*. ``sandbox.create_snapshot(name)`` captures a
sandbox and maps to a DigitalOcean *snapshot* (it cannot be restored yet).
"""

from typing import Any, Callable, Dict, Iterator, List, Optional

from ... import Sandbox as _DoSandbox
from ...errors import NotFoundError, SandboxError, SandboxNotImplementedError
from ...snapshots import Snapshot as _DoSnapshot
from ...templates import Template as _DoTemplate
from .._base import translating
from . import _mirror_v0 as _m
from ._common import (
    SandboxState,
    SnapshotState,
    create_options,
    do_state_filter,
    reject,
    resolve_config,
    snapshot_state,
    state_of,
)
from .exceptions import DaytonaNotFoundError, map_error


class _Mapped:
    """Mixin: the Daytona exception for a failed DigitalOcean call."""

    @staticmethod
    def _map_error(err: SandboxError) -> BaseException:
        return map_error(err)


class Snapshot(_m.Snapshot):
    """A Daytona snapshot: here, a DigitalOcean template."""

    def __init__(self, info: Any) -> None:  # pylint: disable=super-init-not-called
        image = getattr(info, "image", None)
        ref = None
        if image is not None and image.repository:
            ref = (
                "%s/%s" % (image.registry, image.repository)
                if image.registry
                else image.repository
            )
            ref += (":" + image.tag) if image.tag else ""
        self.id = info.template_id
        self.name = info.name
        self.image_name = ref
        self.state = snapshot_state(info.status)
        self.error_reason = None
        self.created_at = info.created_at.isoformat() if info.created_at else None
        self.updated_at = info.updated_at.isoformat() if info.updated_at else None
        for field in (
            "organization_id",
            "general",
            "size",
            "entrypoint",
            "cpu",
            "gpu",
            "mem",
            "disk",
            "last_used_at",
        ):
            setattr(self, field, None)


class SnapshotService(_Mapped, _m.SnapshotService):
    """``daytona.snapshot``: Daytona snapshots are DigitalOcean templates."""

    def __init__(
        self, owner: "Daytona"
    ) -> None:  # pylint: disable=super-init-not-called
        self._owner = owner

    def _templates(self) -> List[Any]:
        pages = _DoTemplate.list(
            **self._owner._conn
        )  # pylint: disable=protected-access
        out: List[Any] = []
        while pages.has_next:
            out.extend(t.info for t in pages.next_items())
        return out

    @translating
    def list(
        self,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        source_sandbox_id: Optional[str] = None,
    ) -> Any:
        reject(
            "SnapshotService.list",
            "listing the snapshots of one sandbox",
            source_sandbox_id=source_sandbox_id,
        )
        items = [Snapshot(t) for t in self._templates()]
        size = limit or 100
        number = page or 1
        total = len(items)
        return _m.PaginatedSnapshots(
            items=items[(number - 1) * size : number * size],
            total=total,
            page=number,
            total_pages=max(1, -(-total // size)),
        )

    @translating
    def get(self, name: str) -> Snapshot:
        for info in self._templates():
            if info.name == name:
                return Snapshot(info)
        raise DaytonaNotFoundError("Snapshot %r not found" % name, status_code=404)

    @translating
    def delete(self, snapshot: Any) -> None:
        name = snapshot if isinstance(snapshot, str) else snapshot.name
        found = self.get(name)
        _DoTemplate.delete(
            found.id, **self._owner._conn
        )  # pylint: disable=protected-access

    @translating
    def create(
        self,
        params: Any,
        *,
        on_logs: Optional[Callable[[str], None]] = None,
        timeout: Optional[float] = 0,
    ) -> Snapshot:
        image = getattr(params, "image", None)
        if not isinstance(image, str):
            raise SandboxNotImplementedError(
                "Daytona.SnapshotService.create(params.image=<Image builder>)",
                "template builds from instructions (pass an OCI image reference as a string)",
            )
        reject(
            "SnapshotService.create",
            "snapshot resources, entrypoint, and region options",
            resources=getattr(params, "resources", None),
            entrypoint=getattr(params, "entrypoint", None),
            region_id=getattr(params, "region_id", None),
        )
        template = _DoTemplate.create(
            name=params.name,
            source_oci_ref=image,
            **self._owner._conn,  # pylint: disable=protected-access
        )
        template.wait_until_ready(timeout=timeout or 600.0)
        return Snapshot(template.info)


class Process(_Mapped, _m.Process):
    """``sandbox.process``: ``exec`` works; sessions, PTY and code run raise."""

    def __init__(
        self, sandbox: "Sandbox"
    ) -> None:  # pylint: disable=super-init-not-called
        self._sandbox = sandbox

    @translating
    def exec(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Any:
        result = self._sandbox._do.commands.run(  # pylint: disable=protected-access
            command, cwd=cwd, env_vars=env, timeout_seconds=timeout
        )
        return _m.ExecuteResponse(
            exit_code=result.exit_code,
            result=(result.stdout or "") + (result.stderr or ""),
            artifacts=None,
        )


class Sandbox(_Mapped, _m.Sandbox):
    """A Daytona sandbox, backed by a DigitalOcean Sandbox."""

    def __init__(
        self, owner: "Daytona", sandbox: _DoSandbox
    ) -> None:  # pylint: disable=super-init-not-called
        self._owner = owner
        self._do = sandbox
        self._process = Process(self)
        self._apply()

    def _apply(self) -> None:
        info = self._do.info
        self.id = info.sandbox_id
        self.name = info.sandbox_id
        self.snapshot = info.template
        self.state = state_of(info.state)
        self.desired_state = self.state
        self.created_at = info.created_at.isoformat() if info.created_at else None
        self.env = {}
        self.labels = {}
        for field in (
            "organization_id",
            "user",
            "public",
            "target",
            "cpu",
            "gpu",
            "memory",
            "disk",
            "error_reason",
            "network_block_all",
            "kvm",
            "network_allow_list",
            "domain_allow_list",
            "volumes",
            "updated_at",
            "last_activity_at",
            "auto_stop_interval",
            "auto_pause_interval",
            "auto_archive_interval",
            "auto_delete_interval",
            "build_info",
            "runner_id",
            "toolbox_proxy_url",
        ):
            setattr(self, field, None)

    @property
    def process(self) -> Process:
        return self._process

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "snapshot": self.snapshot,
            "state": self.state.value,
        }

    @translating
    def refresh_data(self, request_timeout: Optional[float] = None) -> None:
        self._do.get_info()
        self._apply()

    @translating
    def start(self, timeout: Optional[float] = 60) -> None:
        self._do.resume()
        self._apply()

    @translating
    def stop(self, timeout: Optional[float] = 60, force: bool = False) -> None:
        self._do.pause()
        self._apply()

    @translating
    def pause(self, timeout: float = 60) -> None:
        self._do.pause()
        self._apply()

    @translating
    def delete(self, timeout: Optional[float] = 60, wait: bool = False) -> None:
        self._do.kill()

    @translating
    def wait_for_sandbox_start(self, timeout: Optional[float] = 60) -> None:
        self._do.wait_until_running(timeout=timeout or 60)
        self._apply()

    @translating
    def create_snapshot(self, name: str, timeout: Optional[float] = 60) -> None:
        snapshot = self._do.create_snapshot(name=name)
        snapshot.wait_until_ready(timeout=timeout or 300.0)


class Daytona(_Mapped, _m.Daytona):
    """Daytona's ``v0`` client, backed by DigitalOcean Sandboxes.

    ``config.api_key`` is the DigitalOcean API token (default
    ``DIGITALOCEAN_ACCESS_TOKEN``, not ``DAYTONA_API_KEY``).
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        *,
        do_api_url: Optional[str] = None,
        size: Optional[str] = None,
    ) -> None:  # pylint: disable=super-init-not-called
        resolved = resolve_config(
            "Daytona", config, {"do_api_url": do_api_url, "size": size}
        )
        self._conn = {"token": resolved["token"], "api_url": resolved["api_url"]}
        self._size = resolved["size"]
        self.snapshot = SnapshotService(self)
        #: Daytona's volume service (every method raises ``SandboxNotImplementedError``).
        self.volume = _m.VolumeService(self)

    def __enter__(self) -> "Daytona":
        return self

    def __exit__(self, exc_type=None, exc_value=None, traceback=None) -> None:
        self.close()

    def close(self) -> None:
        """Nothing to close: each call manages its own connection."""

    @translating
    def create(
        self,
        params: Optional[Any] = None,
        *,
        timeout: float = 60,
        on_snapshot_create_logs: Optional[Callable[[str], None]] = None,
    ) -> Sandbox:
        template, env_vars, allow = create_options("Daytona.create", params)
        sandbox = _DoSandbox.create(
            template=template,
            size=self._size,
            allow_internet_access=allow,
            env_vars=env_vars,
            **self._conn,
        )
        return Sandbox(self, sandbox)

    @translating
    def delete(self, sandbox: Sandbox, timeout: float = 60, wait: bool = False) -> None:
        sandbox.delete(timeout, wait)

    @translating
    def get(
        self, sandbox_id_or_name: str, request_timeout: Optional[float] = None
    ) -> Sandbox:
        return Sandbox(self, _DoSandbox.get(sandbox_id_or_name, **self._conn))

    @translating
    def list(
        self, query: Optional[Any] = None, request_timeout: Optional[float] = None
    ) -> Iterator[Sandbox]:
        limit = None
        state = None
        if query is not None:
            reject(
                "Daytona.list",
                "sandbox filters by id, name, labels, snapshot, region, size, visibility, or time",
                **{
                    f: getattr(query, f, None)
                    for f in (
                        "id",
                        "name",
                        "labels",
                        "snapshots",
                        "targets",
                        "min_cpu",
                        "max_cpu",
                        "min_memory_gib",
                        "max_memory_gib",
                        "min_disk_gib",
                        "max_disk_gib",
                        "is_public",
                        "is_recoverable",
                        "created_at_after",
                        "created_at_before",
                        "last_activity_after",
                        "last_activity_before",
                        "auto_destroy_at_after",
                        "auto_destroy_at_before",
                        "sort",
                        "order",
                    )
                },
            )
            limit = getattr(query, "limit", None)
            state = do_state_filter(getattr(query, "states", None))
        pages = _DoSandbox.list(state=state, limit=limit, **self._conn)
        return self._iterate(pages)

    def _iterate(self, pages: Any) -> Iterator[Sandbox]:
        while pages.has_next:
            for do in pages.next_items():
                yield Sandbox(self, do)

    @translating
    def start(self, sandbox: Sandbox, timeout: float = 60) -> None:
        sandbox.start(timeout)

    @translating
    def stop(self, sandbox: Sandbox, timeout: float = 60) -> None:
        sandbox.stop(timeout)


__all__ = [
    "Daytona",
    "Process",
    "Sandbox",
    "SandboxState",
    "Snapshot",
    "SnapshotService",
    "SnapshotState",
]
