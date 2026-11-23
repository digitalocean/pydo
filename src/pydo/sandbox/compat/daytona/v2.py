# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Daytona's ``v2`` namespace (daytona 2.1.0) over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. ``Daytona().v2``: ``create``,
``create_from_snapshot`` (a Daytona snapshot is a DigitalOcean template), ``get``,
``list``, ``iter``, ``start``, ``stop``, ``pause``, ``resume``, ``delete``, and on a
sandbox ``exec``, ``wait``, ``refresh_data`` and the lifecycle calls work. Everything
else (files, git, PTY, ports, interpreter, computer use, images, volumes, secrets,
reservations, network policy, lifecycle policy) keeps Daytona's signature and
raises :class:`~pydo.sandbox.errors.SandboxNotImplementedError`.
"""

import time
from typing import Any, Iterator, List, Mapping, Optional, Sequence

from ... import Sandbox as _DoSandbox
from ...errors import SandboxError, SandboxNotImplementedError
from ...types import PAUSED, RUNNING
from .._base import translating
from . import _mirror_v2 as _m
from ._common import reject
from .exceptions import map_error


class _Mapped:
    @staticmethod
    def _map_error(err: SandboxError) -> BaseException:
        return map_error(err)


def _state(do_state: str) -> str:
    if do_state == RUNNING:
        return "started"
    if do_state == PAUSED:
        return "paused"
    return "creating"


class Sandbox(_Mapped, _m.Sandbox):
    """A v2 Daytona sandbox, backed by a DigitalOcean Sandbox."""

    def __init__(
        self, owner: "Daytona", sandbox: _DoSandbox
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
    def refresh_data(self) -> None:
        self._do.get_info()

    @translating
    def start(self, *, timeout: float = 60) -> None:
        self._do.resume()

    @translating
    def resume(self, *, timeout: float = 60) -> None:
        self._do.resume()

    @translating
    def stop(self, *, timeout: float = 60) -> None:
        self._do.pause()

    @translating
    def pause(self, *, timeout: float = 60) -> None:
        self._do.pause()

    @translating
    def delete(self, *, timeout: float = 60) -> None:
        self._do.kill()

    @translating
    def wait(self, *, until: Any = "started", timeout: float = 60) -> "Sandbox":
        targets = [until] if isinstance(until, str) else list(until)
        deadline = time.monotonic() + timeout
        while True:
            self._do.get_info()
            if self.state in targets:
                return self
            if time.monotonic() >= deadline:
                raise SandboxError(
                    "sandbox %s was not %s in time" % (self.id, "/".join(targets))
                )
            time.sleep(1.0)

    @translating
    def create_snapshot(self, name: str, /) -> Any:
        snapshot = self._do.create_snapshot(name=name)
        snapshot.wait_until_ready()
        return _m.Snapshot(id=snapshot.snapshot_id, name=snapshot.name)

    @translating
    def exec(
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
            "Sandbox.exec",
            "running as another user, naming, tagging, and log retention of processes",
            user=user,
            name=name,
            tag=tag,
            keep_logs=keep_logs,
        )
        if stdin != "closed":
            raise SandboxNotImplementedError(
                "Daytona.Sandbox.exec(stdin='open')",
                "an open standard input on exec (start the command and write to it)",
            )
        limit = execution_timeout if execution_timeout is not None else timeout
        seconds = int(limit) if limit else None
        if argv is not None:
            if command is not None:
                raise SandboxError("exec: pass `command` or `argv`, not both")
            exe, args = argv[0], list(argv[1:])
        else:
            exe, args = (shell or "bash"), (
                ["-lc", command]
                if login is not False and not shell
                else ["-c", command]
            )
            if shell is None:
                args = ["-lc" if login is not False else "-c", command]
        cmd = self._do.commands.start(
            exe,
            args=args,
            cwd=cwd,
            env_vars=dict(env) if env else None,
            timeout_seconds=seconds,
        )
        result = cmd.wait()
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


class Daytona(_Mapped, _m.Daytona):
    """Daytona's ``v2`` client, backed by DigitalOcean Sandboxes."""

    def __init__(
        self, conn: Optional[dict] = None, size: Optional[str] = None
    ) -> None:  # pylint: disable=super-init-not-called
        self._conn = dict(conn or {})
        self._size = size

    def close(self) -> None:
        """Nothing to close: each call manages its own connection."""

    def __enter__(self) -> "Daytona":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _make(
        self, template: Optional[str], env: Optional[Mapping[str, str]]
    ) -> Sandbox:
        return Sandbox(
            self,
            _DoSandbox.create(
                template=template,
                size=self._size,
                env_vars=dict(env) if env else None,
                **self._conn,
            ),
        )

    @translating
    def create(
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
    ) -> Sandbox:
        if image is not None:
            raise SandboxNotImplementedError(
                "Daytona.create(image=...)",
                "sandboxes from an image (build a template from the image, then create_from_snapshot)",
            )
        _create_options(
            "Daytona.create",
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
        return self._make(None, env)

    @translating
    def create_from_snapshot(
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
    ) -> Sandbox:
        _create_options(
            "Daytona.create_from_snapshot",
            name=name,
            labels=labels,
            lifecycle_policy=lifecycle_policy,
            ports=ports,
            region=region,
            idempotency_key=idempotency_key,
        )
        return self._make(snapshot, None)

    @translating
    def get(
        self,
        sandbox_id: str,
        *,
        toolbox_url: Optional[str] = None,
        access_token: Optional[str] = None,
    ) -> Sandbox:
        reject(
            "Daytona.get",
            "a toolbox URL or access token",
            toolbox_url=toolbox_url,
            access_token=access_token,
        )
        return Sandbox(self, _DoSandbox.get(sandbox_id, **self._conn))

    @translating
    def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None) -> Any:
        pages = _DoSandbox.list(limit=limit, next_token=cursor, **self._conn)
        items: List[Sandbox] = [Sandbox(self, do) for do in pages.next_items()]
        return _m.ListResult(
            items=items, next_cursor=pages.next_token if pages.has_next else None
        )

    @translating
    def iter(
        self, *, cursor: Optional[str] = None, limit: Optional[int] = None
    ) -> Iterator[Sandbox]:
        pages = _DoSandbox.list(limit=limit, next_token=cursor, **self._conn)
        while pages.has_next:
            for do in pages.next_items():
                yield Sandbox(self, do)

    @staticmethod
    def _do_of(sandbox: Any) -> _DoSandbox:
        return (
            sandbox._do if isinstance(sandbox, Sandbox) else None
        )  # pylint: disable=protected-access

    @translating
    def delete(self, sandbox: Any, *, timeout: float = 60) -> None:
        self._act(sandbox, "kill")

    @translating
    def start(self, sandbox: Any, *, timeout: float = 60) -> None:
        self._act(sandbox, "resume")

    @translating
    def resume(self, sandbox: Any, *, timeout: float = 60) -> None:
        self._act(sandbox, "resume")

    @translating
    def stop(self, sandbox: Any, *, timeout: float = 60) -> None:
        self._act(sandbox, "pause")

    @translating
    def pause(self, sandbox: Any, *, timeout: float = 60) -> None:
        self._act(sandbox, "pause")

    def _act(self, sandbox: Any, verb: str) -> None:
        if isinstance(sandbox, Sandbox):
            getattr(sandbox._do, verb)()  # pylint: disable=protected-access
        elif verb == "kill":
            _DoSandbox.kill(sandbox, **self._conn)
        elif verb == "pause":
            _DoSandbox.pause(sandbox, **self._conn)
        else:
            _DoSandbox.connect(sandbox, **self._conn)


def _create_options(qualified: str, **given: Any) -> None:
    reject(
        qualified,
        "sandbox naming, labels, resources, ports, volumes, secrets, lifecycle, region and idempotency options",
        **given,
    )


__all__ = ["Daytona", "Sandbox"]
