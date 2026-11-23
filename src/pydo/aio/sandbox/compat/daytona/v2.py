# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Daytona's async ``v2`` namespace (daytona 2.1.0) over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. The async twin of
:mod:`pydo.sandbox.compat.daytona.v2`.
"""

import asyncio
import time
from typing import Any, AsyncIterator, List, Mapping, Optional, Sequence

from pydo.aio.sandbox.sandbox import Sandbox as _DoSandbox
from pydo.sandbox.compat._base import translating
from pydo.sandbox.compat.daytona import _mirror_v2 as _m
from pydo.sandbox.compat.daytona._common import reject
from pydo.sandbox.compat.daytona.exceptions import map_error
from pydo.sandbox.compat.daytona.v2 import _create_options, _state
from pydo.sandbox.errors import SandboxError, SandboxNotImplementedError


class _Mapped:
    @staticmethod
    def _map_error(err: SandboxError) -> BaseException:
        return map_error(err)


class AsyncSandbox(_Mapped, _m.AsyncSandbox):
    """A v2 Daytona sandbox, backed by a DigitalOcean Sandbox."""

    def __init__(
        self, owner: "AsyncDaytona", sandbox: _DoSandbox
    ) -> None:  # pylint: disable=super-init-not-called
        self._owner = owner
        self._do = sandbox

    @property
    def id(self) -> str:
        return self._do.sandbox_id

    @property
    def name(self) -> str:
        return self._do.sandbox_id

    @property
    def state(self) -> str:
        return _state(self._do.state)

    @property
    def raw_state(self) -> str:
        return self._do.state

    @property
    def snapshot(self) -> Optional[str]:
        return self._do.template

    @property
    def labels(self) -> Mapping[str, str]:
        return {}

    @property
    def region(self) -> Optional[str]:
        return None

    @translating
    async def refresh_data(self) -> None:
        await self._do.get_info()

    @translating
    async def start(self, *, timeout: float = 60) -> None:
        await self._do.resume()

    @translating
    async def resume(self, *, timeout: float = 60) -> None:
        await self._do.resume()

    @translating
    async def stop(self, *, timeout: float = 60) -> None:
        await self._do.pause()

    @translating
    async def pause(self, *, timeout: float = 60) -> None:
        await self._do.pause()

    @translating
    async def delete(self, *, timeout: float = 60) -> None:
        await self._do.kill()

    @translating
    async def wait(
        self, *, until: Any = "started", timeout: float = 60
    ) -> "AsyncSandbox":
        targets = [until] if isinstance(until, str) else list(until)
        deadline = time.monotonic() + timeout
        while True:
            await self._do.get_info()
            if self.state in targets:
                return self
            if time.monotonic() >= deadline:
                raise SandboxError(
                    "sandbox %s was not %s in time" % (self.id, "/".join(targets))
                )
            await asyncio.sleep(1.0)

    @translating
    async def create_snapshot(self, name: str, /) -> Any:
        snapshot = await self._do.create_snapshot(name=name)
        await snapshot.wait_until_ready()
        return _m.Snapshot(id=snapshot.snapshot_id, name=snapshot.name)

    @translating
    async def exec(
        self,
        command: Optional[str] = None,
        *,
        argv: Optional[Sequence[str]] = None,
        cwd: Optional[str] = None,
        env: Optional[Mapping[str, str]] = None,
        user: Optional[str] = None,
        shell: Optional[str] = None,
        login: Optional[bool] = None,
        stdin: str = "closed",
        timeout: Optional[float] = None,
        execution_timeout: Optional[float] = None,
        name: Optional[str] = None,
        keep_logs: Optional[Any] = None,
        tag: Optional[str] = None,
    ) -> Any:
        reject(
            "AsyncSandbox.exec",
            "running as another user, naming, tagging, and log retention of processes",
            user=user,
            name=name,
            tag=tag,
            keep_logs=keep_logs,
        )
        if stdin != "closed":
            raise SandboxNotImplementedError(
                "Daytona.AsyncSandbox.exec(stdin='open')",
                "an open standard input on exec (start the command and write to it)",
            )
        limit = execution_timeout if execution_timeout is not None else timeout
        seconds = int(limit) if limit else None
        if argv is not None:
            if command is not None:
                raise SandboxError("exec: pass `command` or `argv`, not both")
            exe, args = argv[0], list(argv[1:])
        elif shell:
            exe, args = shell, ["-c", command]
        else:
            exe, args = "bash", ["-lc" if login is not False else "-c", command]
        cmd = await self._do.commands.start(
            exe,
            args=args,
            cwd=cwd,
            env_vars=dict(env) if env else None,
            timeout_seconds=seconds,
        )
        result = await cmd.wait()
        return _m.ProcessResult(
            reason="exited",
            exit_code=result.exit_code,
            signal=None,
            raw_reason="exited",
            process_id=str(cmd.pid),
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            output=(result.stdout or "") + (result.stderr or ""),
            logs=(),
        )


class AsyncDaytona(_Mapped, _m.AsyncDaytona):
    """Daytona's async ``v2`` client, backed by DigitalOcean Sandboxes."""

    def __init__(
        self, conn: Optional[dict] = None, size: Optional[str] = None
    ) -> None:  # pylint: disable=super-init-not-called
        self._conn = dict(conn or {})
        self._size = size

    async def close(self) -> None:
        """Nothing to close: each call manages its own connection."""

    async def __aenter__(self) -> "AsyncDaytona":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def _make(
        self, template: Optional[str], env: Optional[Mapping[str, str]]
    ) -> AsyncSandbox:
        return AsyncSandbox(
            self,
            await _DoSandbox.create(
                template=template,
                size=self._size,
                env_vars=dict(env) if env else None,
                **self._conn,
            ),
        )

    @translating
    async def create(
        self,
        image: Optional[str] = None,
        *,
        name: Optional[str] = None,
        env: Optional[Mapping[str, str]] = None,
        labels: Optional[Mapping[str, str]] = None,
        resources: Optional[Any] = None,
        ports: Optional[Sequence[Any]] = None,
        volumes: Optional[Sequence[Any]] = None,
        secrets: Optional[Sequence[str]] = None,
        spot: Optional[bool] = None,
        user: Optional[str] = None,
        lifecycle_policy: Optional[Any] = None,
        network_policy: Any = None,
        cpu_arch: Optional[str] = None,
        cpu_type: Optional[str] = None,
        region: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        wait_seconds: int = 60,
        create_timeout_seconds: Optional[int] = None,
    ) -> AsyncSandbox:
        if image is not None:
            raise SandboxNotImplementedError(
                "Daytona.AsyncDaytona.create(image=...)",
                "sandboxes from an image (build a template from the image, then create_from_snapshot)",
            )
        _create_options(
            "AsyncDaytona.create",
            name=name,
            labels=labels,
            resources=resources,
            ports=ports,
            volumes=volumes,
            secrets=secrets,
            spot=spot,
            user=user,
            lifecycle_policy=lifecycle_policy,
            cpu_arch=cpu_arch,
            cpu_type=cpu_type,
            region=region,
            idempotency_key=idempotency_key,
        )
        return await self._make(None, env)

    @translating
    async def create_from_snapshot(
        self,
        snapshot: str,
        *,
        name: Optional[str] = None,
        labels: Optional[Mapping[str, str]] = None,
        lifecycle_policy: Optional[Any] = None,
        ports: Optional[Sequence[Any]] = None,
        region: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        wait_seconds: int = 60,
        create_timeout_seconds: Optional[int] = None,
    ) -> AsyncSandbox:
        _create_options(
            "AsyncDaytona.create_from_snapshot",
            name=name,
            labels=labels,
            lifecycle_policy=lifecycle_policy,
            ports=ports,
            region=region,
            idempotency_key=idempotency_key,
        )
        return await self._make(snapshot, None)

    @translating
    async def get(
        self,
        sandbox_id: str,
        *,
        toolbox_url: Optional[str] = None,
        access_token: Optional[str] = None,
    ) -> AsyncSandbox:
        reject(
            "AsyncDaytona.get",
            "a toolbox URL or access token",
            toolbox_url=toolbox_url,
            access_token=access_token,
        )
        return AsyncSandbox(self, await _DoSandbox.get(sandbox_id, **self._conn))

    @translating
    async def list(
        self, *, cursor: Optional[str] = None, limit: Optional[int] = None
    ) -> Any:
        pages = _DoSandbox.list(limit=limit, next_token=cursor, **self._conn)
        items: List[AsyncSandbox] = [
            AsyncSandbox(self, do) for do in await pages.next_items()
        ]
        return _m.ListResult(
            items=items, next_cursor=pages.next_token if pages.has_next else None
        )

    async def iter(
        self, *, cursor: Optional[str] = None, limit: Optional[int] = None
    ) -> AsyncIterator[AsyncSandbox]:
        pages = _DoSandbox.list(limit=limit, next_token=cursor, **self._conn)
        while pages.has_next:
            for do in await pages.next_items():
                yield AsyncSandbox(self, do)

    async def _act(self, sandbox: Any, verb: str) -> None:
        if isinstance(sandbox, AsyncSandbox):
            await getattr(sandbox._do, verb)()  # pylint: disable=protected-access
        elif verb == "kill":
            await _DoSandbox.kill(sandbox, **self._conn)
        elif verb == "pause":
            await _DoSandbox.pause(sandbox, **self._conn)
        else:
            await _DoSandbox.connect(sandbox, **self._conn)

    @translating
    async def delete(self, sandbox: Any, *, timeout: float = 60) -> None:
        await self._act(sandbox, "kill")

    @translating
    async def start(self, sandbox: Any, *, timeout: float = 60) -> None:
        await self._act(sandbox, "resume")

    @translating
    async def resume(self, sandbox: Any, *, timeout: float = 60) -> None:
        await self._act(sandbox, "resume")

    @translating
    async def stop(self, sandbox: Any, *, timeout: float = 60) -> None:
        await self._act(sandbox, "pause")

    @translating
    async def pause(self, sandbox: Any, *, timeout: float = 60) -> None:
        await self._act(sandbox, "pause")


__all__ = ["AsyncDaytona", "AsyncSandbox"]
