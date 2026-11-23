# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Daytona's async ``v0`` namespace (daytona 2.1.0) over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. The async twin of
:mod:`pydo.sandbox.compat.daytona.v0`: ``AsyncDaytona``, ``AsyncSandbox``,
``AsyncProcess`` and ``AsyncSnapshotService``. See there for what works and what
raises :class:`~pydo.sandbox.errors.SandboxNotImplementedError`.
"""

from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from pydo.aio.sandbox.sandbox import Sandbox as _DoSandbox
from pydo.aio.sandbox.templates import Template as _DoTemplate
from pydo.sandbox.compat._base import translating
from pydo.sandbox.compat.daytona import _mirror_v0 as _m
from pydo.sandbox.compat.daytona._common import (
    create_options,
    do_state_filter,
    reject,
    resolve_config,
    state_of,
)
from pydo.sandbox.compat.daytona.exceptions import DaytonaNotFoundError, map_error
from pydo.sandbox.compat.daytona.v0 import Snapshot
from pydo.sandbox.errors import SandboxError, SandboxNotImplementedError


class _Mapped:
    @staticmethod
    def _map_error(err: SandboxError) -> BaseException:
        return map_error(err)


class AsyncSnapshotService(_Mapped, _m.AsyncSnapshotService):
    """``daytona.snapshot``: Daytona snapshots are DigitalOcean templates."""

    def __init__(
        self, owner: "AsyncDaytona"
    ) -> None:  # pylint: disable=super-init-not-called
        self._owner = owner

    async def _templates(self) -> List[Any]:
        pages = _DoTemplate.list(
            **self._owner._conn
        )  # pylint: disable=protected-access
        out: List[Any] = []
        while pages.has_next:
            out.extend(t.info for t in await pages.next_items())
        return out

    @translating
    async def list(
        self,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        source_sandbox_id: Optional[str] = None,
    ) -> Any:
        reject(
            "AsyncSnapshotService.list",
            "listing the snapshots of one sandbox",
            source_sandbox_id=source_sandbox_id,
        )
        items = [Snapshot(t) for t in await self._templates()]
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
    async def get(self, name: str) -> Snapshot:
        for info in await self._templates():
            if info.name == name:
                return Snapshot(info)
        raise DaytonaNotFoundError("Snapshot %r not found" % name, status_code=404)

    @translating
    async def delete(self, snapshot: Any) -> None:
        name = snapshot if isinstance(snapshot, str) else snapshot.name
        found = await self.get(name)
        await _DoTemplate.delete(
            found.id, **self._owner._conn
        )  # pylint: disable=protected-access

    @translating
    async def create(
        self,
        params: Any,
        *,
        on_logs: Optional[Callable[[str], None]] = None,
        timeout: Optional[float] = 0,
    ) -> Snapshot:
        image = getattr(params, "image", None)
        if not isinstance(image, str):
            raise SandboxNotImplementedError(
                "Daytona.AsyncSnapshotService.create(params.image=<Image builder>)",
                "template builds from instructions (pass an OCI image reference as a string)",
            )
        reject(
            "AsyncSnapshotService.create",
            "snapshot resources, entrypoint, and region options",
            resources=getattr(params, "resources", None),
            entrypoint=getattr(params, "entrypoint", None),
            region_id=getattr(params, "region_id", None),
        )
        template = await _DoTemplate.create(
            name=params.name,
            source_oci_ref=image,
            **self._owner._conn,  # pylint: disable=protected-access
        )
        await template.wait_until_ready(timeout=timeout or 600.0)
        return Snapshot(template.info)


class AsyncProcess(_Mapped, _m.AsyncProcess):
    """``sandbox.process``: ``exec`` works; sessions, PTY and code run raise."""

    def __init__(
        self, sandbox: "AsyncSandbox"
    ) -> None:  # pylint: disable=super-init-not-called
        self._sandbox = sandbox

    @translating
    async def exec(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Any:
        result = (
            await self._sandbox._do.commands.run(  # pylint: disable=protected-access
                command, cwd=cwd, env_vars=env, timeout_seconds=timeout
            )
        )
        return _m.ExecuteResponse(
            exit_code=result.exit_code,
            result=(result.stdout or "") + (result.stderr or ""),
            artifacts=None,
        )


class AsyncSandbox(_Mapped, _m.AsyncSandbox):
    """A Daytona sandbox, backed by a DigitalOcean Sandbox."""

    def __init__(
        self, owner: "AsyncDaytona", sandbox: _DoSandbox
    ) -> None:  # pylint: disable=super-init-not-called
        self._owner = owner
        self._do = sandbox
        self._process = AsyncProcess(self)
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
    def process(self) -> AsyncProcess:
        return self._process

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "snapshot": self.snapshot,
            "state": self.state.value,
        }

    @translating
    async def refresh_data(self, request_timeout: Optional[float] = None) -> None:
        await self._do.get_info()
        self._apply()

    @translating
    async def start(self, timeout: Optional[float] = 60) -> None:
        await self._do.resume()
        self._apply()

    @translating
    async def stop(self, timeout: Optional[float] = 60, force: bool = False) -> None:
        await self._do.pause()
        self._apply()

    @translating
    async def pause(self, timeout: float = 60) -> None:
        await self._do.pause()
        self._apply()

    @translating
    async def delete(self, timeout: Optional[float] = 60, wait: bool = False) -> None:
        await self._do.kill()

    @translating
    async def wait_for_sandbox_start(self, timeout: Optional[float] = 60) -> None:
        await self._do.wait_until_running(timeout=timeout or 60)
        self._apply()

    @translating
    async def create_snapshot(self, name: str, timeout: Optional[float] = 60) -> None:
        snapshot = await self._do.create_snapshot(name=name)
        await snapshot.wait_until_ready(timeout=timeout or 300.0)


class AsyncDaytona(_Mapped, _m.AsyncDaytona):
    """Daytona's async ``v0`` client, backed by DigitalOcean Sandboxes."""

    def __init__(
        self,
        config: Optional[Any] = None,
        *,
        do_api_url: Optional[str] = None,
        size: Optional[str] = None,
    ) -> None:  # pylint: disable=super-init-not-called
        resolved = resolve_config(
            "AsyncDaytona", config, {"do_api_url": do_api_url, "size": size}
        )
        self._conn = {"token": resolved["token"], "api_url": resolved["api_url"]}
        self._size = resolved["size"]
        self.snapshot = AsyncSnapshotService(self)
        #: Daytona's volume service (every method raises ``SandboxNotImplementedError``).
        self.volume = _m.AsyncVolumeService(self)

    async def __aenter__(self) -> "AsyncDaytona":
        return self

    async def __aexit__(self, exc_type=None, exc_value=None, traceback=None) -> None:
        await self.close()

    async def close(self) -> None:
        """Nothing to close: each call manages its own connection."""

    @translating
    async def create(
        self,
        params: Optional[Any] = None,
        *,
        timeout: float = 60,
        on_snapshot_create_logs: Optional[Callable[[str], None]] = None,
    ) -> AsyncSandbox:
        template, env_vars, allow = create_options("AsyncDaytona.create", params)
        sandbox = await _DoSandbox.create(
            template=template,
            size=self._size,
            allow_internet_access=allow,
            env_vars=env_vars,
            **self._conn,
        )
        return AsyncSandbox(self, sandbox)

    @translating
    async def delete(
        self, sandbox: AsyncSandbox, timeout: float = 60, wait: bool = False
    ) -> None:
        await sandbox.delete(timeout, wait)

    @translating
    async def get(
        self, sandbox_id_or_name: str, request_timeout: Optional[float] = None
    ) -> AsyncSandbox:
        return AsyncSandbox(
            self, await _DoSandbox.get(sandbox_id_or_name, **self._conn)
        )

    @translating
    async def list(
        self, query: Optional[Any] = None, request_timeout: Optional[float] = None
    ) -> AsyncIterator[AsyncSandbox]:
        limit = None
        state = None
        if query is not None:
            reject(
                "AsyncDaytona.list",
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

    async def _iterate(self, pages: Any) -> AsyncIterator[AsyncSandbox]:
        while pages.has_next:
            for do in await pages.next_items():
                yield AsyncSandbox(self, do)

    @translating
    async def start(self, sandbox: AsyncSandbox, timeout: float = 60) -> None:
        await sandbox.start(timeout)

    @translating
    async def stop(self, sandbox: AsyncSandbox, timeout: float = 60) -> None:
        await sandbox.stop(timeout)


__all__ = ["AsyncDaytona", "AsyncProcess", "AsyncSandbox", "AsyncSnapshotService"]
