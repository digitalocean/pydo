# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""E2B ``Sandbox`` (e2b 2.64.0) over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. Migration only: keep
``from e2b import Sandbox`` working by importing it from here instead. Methods
the Sandboxes API cannot serve keep E2B's signature and raise
:class:`~pydo.sandbox.errors.SandboxNotImplementedError` (see ``_mirror.py``).
"""

import logging
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple, Union

from ... import Sandbox as _DoSandbox
from ...commands import Command as _DoCommand
from ...errors import NotFoundError, SandboxError, SandboxNotImplementedError
from ...snapshots import Snapshot as _DoSnapshot
from .._base import reject, translating
from ..._hybrid import by_id_or_self
from . import _mirror as _m
from ._common import (
    CommandExitException,
    CommandResult,
    SandboxState,
    check_pause_options,
    connection,
    no_list_options,
    process_info,
    reject_lifetime,
    sandbox_info,
    snapshot_info,
    state_filter,
)
from .exceptions import map_error


class _Mapped:
    """Mixin: the E2B exception for a failed DigitalOcean call."""

    @staticmethod
    def _map_error(err: SandboxError) -> BaseException:
        return map_error(err)


class CommandHandle(_Mapped, _m.CommandHandle):
    """A command running in the sandbox (``commands.run(..., background=True)``)."""

    def __init__(
        self, command: _DoCommand, retain_output: bool = True
    ) -> None:  # pylint: disable=super-init-not-called
        self._cmd = command
        self._retain = retain_output
        self._pid = command.pid

    @property
    def pid(self) -> int:
        return self._pid

    def __iter__(self) -> Iterator[Tuple[Optional[str], Optional[str], None]]:
        for event in self._cmd.stream():
            if event.type == "stdout":
                yield event.text, None, None
            elif event.type == "stderr":
                yield None, event.text, None

    def disconnect(self) -> None:
        """Stops reading output; the command keeps running."""

    @translating
    def wait(
        self,
        on_pty: Optional[Callable[[bytes], None]] = None,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        if on_pty is not None:
            raise SandboxNotImplementedError(
                "E2B.CommandHandle.wait(on_pty=...)", "a PTY (interactive terminal) API"
            )
        result = self._cmd.wait(on_stdout=on_stdout, on_stderr=on_stderr)
        return _finish(result, self._retain)

    @translating
    def kill(self) -> bool:
        try:
            self._cmd.kill()
            return True
        except NotFoundError:
            return False

    @translating
    def send_stdin(
        self, data: Union[str, bytes], request_timeout: Optional[float] = None
    ) -> None:
        self._cmd.write_stdin(data)

    @translating
    def close_stdin(self, request_timeout: Optional[float] = None) -> None:
        self._cmd.close_stdin()


def _finish(result: Any, retain: bool) -> CommandResult:
    out = CommandResult(
        stderr=result.stderr if retain else None,
        stdout=result.stdout if retain else None,
        exit_code=result.exit_code,
        error=result.error,
    )
    if result.exit_code != 0:
        raise CommandExitException(out.stderr, out.stdout, out.exit_code, out.error)
    return out


class Commands(_Mapped, _m.Commands):
    """``sandbox.commands``."""

    def __init__(
        self, sandbox: "Sandbox"
    ) -> None:  # pylint: disable=super-init-not-called
        self._sandbox = sandbox

    @property
    def _do(self):
        return self._sandbox._do.commands  # pylint: disable=protected-access

    @translating
    def list(self, request_timeout: Optional[float] = None) -> List[Any]:
        return [process_info(c) for c in self._do.list()]

    @translating
    def kill(self, pid: int, request_timeout: Optional[float] = None) -> bool:
        try:
            self._do.connect(pid).kill()
            return True
        except NotFoundError:
            return False

    @translating
    def send_stdin(
        self, pid: int, data: Union[str, bytes], request_timeout: Optional[float] = None
    ):
        self._do.connect(pid).write_stdin(data)

    @translating
    def stream_input(self, pid: int, data, *, timeout: Optional[float] = 60.0) -> None:
        command = self._do.connect(pid)
        for chunk in data:
            command.write_stdin(chunk)
        command.close_stdin()

    @translating
    def close_stdin(self, pid: int, request_timeout: Optional[float] = None) -> None:
        self._do.connect(pid).close_stdin()

    @translating
    def run(
        self,
        cmd: str,
        background: Union[bool, None] = None,
        envs: Optional[Dict[str, str]] = None,
        user: Optional[str] = None,
        cwd: Optional[str] = None,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
        stdin: Optional[bool] = None,
        timeout: Optional[float] = 60,
        request_timeout: Optional[float] = None,
        *,
        retain_output: bool = True,
        shell: Optional[Sequence[str]] = None,
    ):
        reject("e2b", "Commands.run", "running commands as another user", user=user)
        if background and (on_stdout or on_stderr):
            raise SandboxNotImplementedError(
                "E2B.Commands.run(background=True, on_stdout=...)",
                "streaming callbacks on a background command (call handle.wait(on_stdout=...))",
            )
        if shell is not None or stdin or background:
            argv = list(shell) if shell else ["bash", "-l", "-c"]
            command = self._do.start(
                argv[0],
                args=argv[1:] + [cmd],
                cwd=cwd,
                env_vars=envs,
                stdin=bool(stdin),
            )
            handle = CommandHandle(command, retain_output)
            if background:
                return handle
            return handle.wait(on_stdout=on_stdout, on_stderr=on_stderr)
        result = self._do.run(
            cmd, cwd=cwd, env_vars=envs, on_stdout=on_stdout, on_stderr=on_stderr
        )
        return _finish(result, retain_output)

    @translating
    def connect(
        self,
        pid: int,
        timeout: Optional[float] = 60,
        request_timeout: Optional[float] = None,
        *,
        retain_output: bool = True,
    ):
        return CommandHandle(self._do.connect(pid), retain_output)


class SandboxPaginator(_Mapped, _m.SandboxPaginator):
    """Pages of sandboxes: ``while paginator.has_next: paginator.next_items()``."""

    def __init__(
        self,
        pages: Any,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        **opts: Any,
    ) -> None:  # pylint: disable=super-init-not-called
        self._pages = pages
        self.limit = limit

    @property
    def has_next(self) -> bool:
        return self._pages.has_next

    @property
    def next_token(self) -> Optional[str]:
        return self._pages.next_token

    @translating
    def next_items(self, **opts: Any) -> List[Any]:
        if not self.has_next:
            raise Exception("No more items to fetch")
        return [sandbox_info(s.info) for s in self._pages.next_items()]


class SnapshotPaginator(_Mapped, _m.SnapshotPaginator):
    """Pages of snapshots."""

    def __init__(
        self,
        pages: Any,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        **opts: Any,
    ) -> None:  # pylint: disable=super-init-not-called
        self._pages = pages
        self.limit = limit

    @property
    def has_next(self) -> bool:
        return self._pages.has_next

    @property
    def next_token(self) -> Optional[str]:
        return self._pages.next_token

    @translating
    def next_items(self, **opts: Any) -> List[Any]:
        if not self.has_next:
            raise Exception("No more items to fetch")
        return [snapshot_info(s) for s in self._pages.next_items()]


class Sandbox(_Mapped, _m.Sandbox):
    """E2B's ``Sandbox``, backed by a DigitalOcean Sandbox.

    ``Sandbox.create()``, ``connect()``, ``kill()``, ``pause()``, the
    ``commands`` and snapshots work. Files, PTY, git, ports, metrics, lifetime
    timeouts and metadata raise ``SandboxNotImplementedError``.
    """

    #: Token, API origin and size a bound client fills in (see ``E2bClient``).
    _defaults: Dict[str, Any] = {}

    def __init__(
        self,
        _sandbox: Optional[_DoSandbox] = None,
        _conn: Optional[Dict[str, Any]] = None,
        **opts: Any,
    ) -> None:  # pylint: disable=super-init-not-called
        if _sandbox is None:
            raise SandboxError(
                "Sandbox() cannot be called directly: use Sandbox.create() or Sandbox.connect()"
            )
        self._do = _sandbox
        self._conn = _conn or {}
        self._commands = Commands(self)

    @classmethod
    def _wrap(
        cls, sandbox: _DoSandbox, token: Optional[str], api_url: Optional[str]
    ) -> "Sandbox":
        return cls(_sandbox=sandbox, _conn={"token": token, "api_url": api_url})

    @property
    def sandbox_id(self) -> str:
        return self._do.sandbox_id

    @property
    def sandbox_domain(self) -> Optional[str]:
        return None

    @property
    def traffic_access_token(self) -> Optional[str]:
        return None

    @property
    def files(self) -> _m.Filesystem:
        return self._child(_m.Filesystem)

    @property
    def commands(self) -> Commands:
        return self._commands

    @property
    def pty(self) -> _m.Pty:
        return self._child(_m.Pty)

    @property
    def git(self) -> _m.Git:
        return self._child(_m.Git)

    def __enter__(self) -> "Sandbox":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.kill()

    @translating
    def is_running(self, request_timeout: Optional[float] = None) -> bool:
        return self._do.is_running()

    @classmethod
    @translating
    def create(
        cls,
        template: Optional[str] = None,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
        envs: Optional[Dict[str, str]] = None,
        secure: Optional[bool] = None,
        allow_internet_access: Optional[bool] = None,
        mcp: Optional[Any] = None,
        network: Optional[Any] = None,
        iam: Optional[Any] = None,
        lifecycle: Optional[Any] = None,
        volume_mounts: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
        idempotency_key: Optional[str] = None,
        *,
        cpu_count: Optional[int] = None,
        **opts: Any,
    ) -> "Sandbox":
        reject_lifetime("Sandbox.create", timeout=timeout, lifecycle=lifecycle)
        reject(
            "e2b",
            "Sandbox.create",
            "sandbox metadata, MCP, network policy, IAM, volume, size, and idempotency options",
            metadata=metadata,
            mcp=mcp,
            network=network,
            iam=iam,
            volume_mounts=volume_mounts,
            idempotency_key=idempotency_key,
            cpu_count=cpu_count,
        )
        if secure is False:
            raise SandboxNotImplementedError(
                "E2B.Sandbox.create(secure=False)", "an unauthenticated sandbox option"
            )
        token, api_url = connection("Sandbox.create", opts, cls._defaults)
        sandbox = _DoSandbox.create(
            template=template,
            size=cls._defaults.get("size"),
            allow_internet_access=allow_internet_access,
            env_vars=envs,
            token=token,
            api_url=api_url,
        )
        return cls._wrap(sandbox, token, api_url)

    @by_id_or_self
    @translating
    def connect(
        self, timeout: Optional[int] = None, *, on_resume: str = "restore", **opts: Any
    ) -> "Sandbox":
        _check_connect("Sandbox.connect", timeout, on_resume)
        if not self._do.is_running():
            self._do.resume()
        return self

    @connect.by_id
    @translating
    def connect(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        sandbox_id: str,
        timeout: Optional[int] = None,
        logger: Optional[logging.Logger] = None,
        *,
        on_resume: str = "restore",
        **opts: Any,
    ) -> "Sandbox":
        _check_connect("Sandbox.connect", timeout, on_resume)
        token, api_url = connection("Sandbox.connect", opts, cls._defaults)
        return cls._wrap(
            _DoSandbox.connect(sandbox_id, token=token, api_url=api_url), token, api_url
        )

    @by_id_or_self
    @translating
    def kill(self, **opts: Any) -> bool:
        return self._do.kill()

    @kill.by_id
    @translating
    def kill(cls, sandbox_id: str, **opts: Any) -> bool:  # type: ignore[no-redef]  # pylint: disable=function-redefined
        token, api_url = connection("Sandbox.kill", opts, cls._defaults)
        return _DoSandbox.kill(sandbox_id, token=token, api_url=api_url)

    @by_id_or_self
    @translating
    def pause(
        self,
        keep_memory: Optional[bool] = None,
        *,
        mode: Optional[str] = None,
        strict: bool = False,
        **opts: Any,
    ) -> bool:
        check_pause_options("Sandbox.pause", keep_memory, mode)
        self._do.pause()
        return True

    @pause.by_id
    @translating
    def pause(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        sandbox_id: str,
        keep_memory: Optional[bool] = None,
        *,
        mode: Optional[str] = None,
        strict: bool = False,
        **opts: Any,
    ) -> bool:
        check_pause_options("Sandbox.pause", keep_memory, mode)
        token, api_url = connection("Sandbox.pause", opts, cls._defaults)
        _DoSandbox.pause(sandbox_id, token=token, api_url=api_url)
        return True

    beta_pause = pause

    @by_id_or_self
    @translating
    def get_info(self, **opts: Any) -> Any:
        return sandbox_info(self._do.get_info())

    @get_info.by_id
    @translating
    def get_info(cls, sandbox_id: str, **opts: Any) -> Any:  # type: ignore[no-redef]  # pylint: disable=function-redefined
        token, api_url = connection("Sandbox.get_info", opts, cls._defaults)
        return sandbox_info(
            _DoSandbox.get(sandbox_id, token=token, api_url=api_url).get_info()
        )

    @by_id_or_self
    @translating
    def create_snapshot(
        self, name: Optional[str] = None, *, mode: Optional[str] = None, **opts: Any
    ) -> Any:
        if mode is not None:
            raise SandboxNotImplementedError(
                "E2B.Sandbox.create_snapshot(mode=...)", "a snapshot mode option"
            )
        snapshot = self._do.create_snapshot(name=name)
        snapshot.wait_until_ready()
        return snapshot_info(snapshot)

    @create_snapshot.by_id
    @translating
    def create_snapshot(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        sandbox_id: str,
        name: Optional[str] = None,
        *,
        mode: Optional[str] = None,
        **opts: Any,
    ) -> Any:
        if mode is not None:
            raise SandboxNotImplementedError(
                "E2B.Sandbox.create_snapshot(mode=...)", "a snapshot mode option"
            )
        token, api_url = connection("Sandbox.create_snapshot", opts, cls._defaults)
        snapshot = _DoSnapshot.create(
            sandbox_id, name=name, token=token, api_url=api_url
        )
        snapshot.wait_until_ready()
        return snapshot_info(snapshot)

    @by_id_or_self
    @translating
    def list_snapshots(
        self,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        name: Optional[str] = None,
        **opts: Any,
    ) -> SnapshotPaginator:
        _no_name_filter(name)
        pages = _DoSnapshot.list(
            sandbox_id=self._do.sandbox_id,
            limit=limit,
            next_token=next_token,
            token=self._conn.get("token"),
            api_url=self._conn.get("api_url"),
        )
        return SnapshotPaginator(pages, limit, next_token)

    @list_snapshots.by_id
    @translating
    def list_snapshots(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        sandbox_id: Optional[str] = None,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        name: Optional[str] = None,
        **opts: Any,
    ) -> SnapshotPaginator:
        _no_name_filter(name)
        token, api_url = connection("Sandbox.list_snapshots", opts, cls._defaults)
        pages = _DoSnapshot.list(
            sandbox_id=sandbox_id,
            limit=limit,
            next_token=next_token,
            token=token,
            api_url=api_url,
        )
        return SnapshotPaginator(pages, limit, next_token)

    @classmethod
    @translating
    def delete_snapshot(cls, snapshot_id: str, **opts: Any) -> bool:
        token, api_url = connection("Sandbox.delete_snapshot", opts, cls._defaults)
        return _DoSnapshot.delete(snapshot_id, token=token, api_url=api_url)

    @classmethod
    @translating
    def list(
        cls,
        query: Optional[Any] = None,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        order: Optional[str] = None,
        **opts: Any,
    ) -> SandboxPaginator:
        no_list_options(order)
        state = state_filter(query)
        token, api_url = connection("Sandbox.list", opts, cls._defaults)
        pages = _DoSandbox.list(
            state=state,
            limit=limit,
            next_token=next_token,
            token=token,
            api_url=api_url,
        )
        return SandboxPaginator(pages, limit, next_token)


def _check_connect(qualified: str, timeout: Optional[int], on_resume: str) -> None:
    reject_lifetime(qualified, timeout=timeout)
    if on_resume != "restore":
        raise SandboxNotImplementedError(
            "E2B.%s(on_resume=%r)" % (qualified, on_resume), "a reboot-on-resume option"
        )


def _no_name_filter(name: Optional[str]) -> None:
    if name is not None:
        raise SandboxNotImplementedError(
            "E2B.Sandbox.list_snapshots(name=...)", "a snapshot name filter"
        )


__all__ = [
    "CommandHandle",
    "Commands",
    "Sandbox",
    "SandboxPaginator",
    "SnapshotPaginator",
]
