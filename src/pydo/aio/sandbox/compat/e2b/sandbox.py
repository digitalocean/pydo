# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""E2B ``AsyncSandbox`` (e2b 2.64.0) over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. The async twin of
:mod:`pydo.sandbox.compat.e2b.sandbox`; see there for what works and what
raises :class:`~pydo.sandbox.errors.SandboxNotImplementedError`.
"""

import logging
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from pydo.sandbox._hybrid import by_id_or_self
from pydo.sandbox.compat import _base
from pydo.sandbox.compat._base import reject, translating
from pydo.sandbox.compat.e2b import _mirror as _m
from pydo.sandbox.compat.e2b._common import (
    CommandExitException,
    CommandResult,
    check_pause_options,
    connection,
    no_list_options,
    process_info,
    reject_lifetime,
    sandbox_info,
    snapshot_info,
    state_filter,
)
from pydo.sandbox.compat.e2b.exceptions import map_error
from pydo.sandbox.errors import NotFoundError, SandboxError, SandboxNotImplementedError
from pydo.aio.sandbox.commands import Command as _DoCommand
from pydo.aio.sandbox.sandbox import Sandbox as _DoSandbox
from pydo.aio.sandbox.snapshots import Snapshot as _DoSnapshot


class _Mapped:
    """Mixin: the E2B exception for a failed DigitalOcean call."""

    @staticmethod
    def _map_error(err: SandboxError) -> BaseException:
        return map_error(err)


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


class AsyncCommandHandle(_Mapped, _m.AsyncCommandHandle):
    """A command running in the sandbox (``commands.run(..., background=True)``)."""

    def __init__(
        self, command: _DoCommand, retain_output: bool = True
    ) -> None:  # pylint: disable=super-init-not-called
        self._cmd = command
        self._retain = retain_output

    @property
    def pid(self) -> int:
        return self._cmd.pid

    async def __aiter__(
        self,
    ) -> AsyncIterator[Tuple[Optional[str], Optional[str], None]]:
        async for event in self._cmd.stream():
            if event.type == "stdout":
                yield event.text, None, None
            elif event.type == "stderr":
                yield None, event.text, None

    async def disconnect(self) -> None:
        """Stops reading output; the command keeps running."""

    @translating
    async def wait(
        self,
        on_pty: Optional[Callable[[bytes], None]] = None,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        if on_pty is not None:
            raise SandboxNotImplementedError(
                "E2B.AsyncCommandHandle.wait(on_pty=...)",
                "a PTY (interactive terminal) API",
            )
        result = await self._cmd.wait(on_stdout=on_stdout, on_stderr=on_stderr)
        return _finish(result, self._retain)

    @translating
    async def kill(self) -> bool:
        try:
            await self._cmd.kill()
            return True
        except NotFoundError:
            return False

    @translating
    async def send_stdin(
        self, data: Union[str, bytes], request_timeout: Optional[float] = None
    ) -> None:
        await self._cmd.write_stdin(data)

    @translating
    async def close_stdin(self, request_timeout: Optional[float] = None) -> None:
        await self._cmd.close_stdin()


class AsyncCommands(_Mapped, _m.AsyncCommands):
    """``sandbox.commands``."""

    def __init__(
        self, sandbox: "AsyncSandbox"
    ) -> None:  # pylint: disable=super-init-not-called
        self._sandbox = sandbox

    @property
    def _do(self):
        return self._sandbox._do.commands  # pylint: disable=protected-access

    @translating
    async def list(self, request_timeout: Optional[float] = None) -> List[Any]:
        return [process_info(c) for c in await self._do.list()]

    @translating
    async def kill(self, pid: int, request_timeout: Optional[float] = None) -> bool:
        try:
            await self._do.connect(pid).kill()
            return True
        except NotFoundError:
            return False

    @translating
    async def send_stdin(
        self, pid: int, data: Union[str, bytes], request_timeout: Optional[float] = None
    ):
        await self._do.connect(pid).write_stdin(data)

    @translating
    async def close_stdin(
        self, pid: int, request_timeout: Optional[float] = None
    ) -> None:
        await self._do.connect(pid).close_stdin()

    @translating
    async def run(
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
        reject(
            "e2b", "AsyncCommands.run", "running commands as another user", user=user
        )
        if background and (on_stdout or on_stderr):
            raise SandboxNotImplementedError(
                "E2B.AsyncCommands.run(background=True, on_stdout=...)",
                "streaming callbacks on a background command (call handle.wait(on_stdout=...))",
            )
        if shell is not None or stdin or background:
            argv = list(shell) if shell else ["bash", "-l", "-c"]
            command = await self._do.start(
                argv[0],
                args=argv[1:] + [cmd],
                cwd=cwd,
                env_vars=envs,
                stdin=bool(stdin),
            )
            handle = AsyncCommandHandle(command, retain_output)
            if background:
                return handle
            return await handle.wait(on_stdout=on_stdout, on_stderr=on_stderr)
        result = await self._do.run(
            cmd, cwd=cwd, env_vars=envs, on_stdout=on_stdout, on_stderr=on_stderr
        )
        return _finish(result, retain_output)

    @translating
    async def connect(
        self,
        pid: int,
        timeout: Optional[float] = 60,
        request_timeout: Optional[float] = None,
        *,
        retain_output: bool = True,
    ):
        return AsyncCommandHandle(self._do.connect(pid), retain_output)


class _AsyncPaginator(_Mapped):
    def __init__(
        self,
        pages: Any,
        convert: Callable[[Any], Any],
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        **opts: Any,
    ) -> None:
        self._pages = pages
        self._convert = convert
        self.limit = limit

    @property
    def has_next(self) -> bool:
        return self._pages.has_next

    @property
    def next_token(self) -> Optional[str]:
        return self._pages.next_token

    @translating
    async def next_items(self, **opts: Any) -> List[Any]:
        if not self.has_next:
            raise Exception("No more items to fetch")
        return [self._convert(item) for item in await self._pages.next_items()]


class AsyncSandboxPaginator(_AsyncPaginator, _m.AsyncSandboxPaginator):
    """Pages of sandboxes: ``while paginator.has_next: await paginator.next_items()``."""

    def __init__(
        self,
        pages: Any,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        **opts: Any,
    ) -> None:
        _AsyncPaginator.__init__(
            self, pages, lambda s: sandbox_info(s.info), limit, next_token
        )


class AsyncSnapshotPaginator(_AsyncPaginator, _m.AsyncSnapshotPaginator):
    """Pages of snapshots."""

    def __init__(
        self,
        pages: Any,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        **opts: Any,
    ) -> None:
        _AsyncPaginator.__init__(self, pages, snapshot_info, limit, next_token)


class AsyncSandbox(_Mapped, _m.AsyncSandbox):
    """E2B's ``AsyncSandbox``, backed by a DigitalOcean Sandbox."""

    _defaults: Dict[str, Any] = {}

    def __init__(
        self,
        _sandbox: Optional[_DoSandbox] = None,
        _conn: Optional[Dict[str, Any]] = None,
        **opts: Any,
    ) -> None:  # pylint: disable=super-init-not-called
        if _sandbox is None:
            raise SandboxError(
                "AsyncSandbox() cannot be called directly: use await AsyncSandbox.create() or AsyncSandbox.connect()"
            )
        self._do = _sandbox
        self._conn = _conn or {}
        self._commands = AsyncCommands(self)

    @classmethod
    def _wrap(
        cls, sandbox: _DoSandbox, token: Optional[str], api_url: Optional[str]
    ) -> "AsyncSandbox":
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
    def files(self) -> _m.AsyncFilesystem:
        return self._child(_m.AsyncFilesystem)

    @property
    def commands(self) -> AsyncCommands:
        return self._commands

    @property
    def pty(self) -> _m.AsyncPty:
        return self._child(_m.AsyncPty)

    @property
    def git(self) -> _m.AsyncGit:
        return self._child(_m.AsyncGit)

    async def __aenter__(self) -> "AsyncSandbox":
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.kill()

    @translating
    async def is_running(self, request_timeout: Optional[float] = None) -> bool:
        return await self._do.is_running()

    @classmethod
    @translating
    async def create(
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
    ) -> "AsyncSandbox":
        reject_lifetime("AsyncSandbox.create", timeout=timeout, lifecycle=lifecycle)
        reject(
            "e2b",
            "AsyncSandbox.create",
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
                "E2B.AsyncSandbox.create(secure=False)",
                "an unauthenticated sandbox option",
            )
        token, api_url = connection("AsyncSandbox.create", opts, cls._defaults)
        sandbox = await _DoSandbox.create(
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
    async def connect(
        self, timeout: Optional[int] = None, *, on_resume: str = "restore", **opts: Any
    ) -> "AsyncSandbox":
        _check_connect("AsyncSandbox.connect", timeout, on_resume)
        if not await self._do.is_running():
            await self._do.resume()
        return self

    @connect.by_id
    @translating
    async def connect(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        sandbox_id: str,
        timeout: Optional[int] = None,
        logger: Optional[logging.Logger] = None,
        *,
        on_resume: str = "restore",
        **opts: Any,
    ) -> "AsyncSandbox":
        _check_connect("AsyncSandbox.connect", timeout, on_resume)
        token, api_url = connection("AsyncSandbox.connect", opts, cls._defaults)
        return cls._wrap(
            await _DoSandbox.connect(sandbox_id, token=token, api_url=api_url),
            token,
            api_url,
        )

    @by_id_or_self
    @translating
    async def kill(self, **opts: Any) -> bool:
        return await self._do.kill()

    @kill.by_id
    @translating
    async def kill(cls, sandbox_id: str, **opts: Any) -> bool:  # type: ignore[no-redef]  # pylint: disable=function-redefined
        token, api_url = connection("AsyncSandbox.kill", opts, cls._defaults)
        return await _DoSandbox.kill(sandbox_id, token=token, api_url=api_url)

    @by_id_or_self
    @translating
    async def pause(
        self,
        keep_memory: Optional[bool] = None,
        *,
        mode: Optional[str] = None,
        strict: bool = False,
        **opts: Any,
    ) -> bool:
        check_pause_options("AsyncSandbox.pause", keep_memory, mode)
        await self._do.pause()
        return True

    @pause.by_id
    @translating
    async def pause(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        sandbox_id: str,
        keep_memory: Optional[bool] = None,
        *,
        mode: Optional[str] = None,
        strict: bool = False,
        **opts: Any,
    ) -> bool:
        check_pause_options("AsyncSandbox.pause", keep_memory, mode)
        token, api_url = connection("AsyncSandbox.pause", opts, cls._defaults)
        await _DoSandbox.pause(sandbox_id, token=token, api_url=api_url)
        return True

    beta_pause = pause

    @by_id_or_self
    @translating
    async def get_info(self, **opts: Any) -> Any:
        return sandbox_info(await self._do.get_info())

    @get_info.by_id
    @translating
    async def get_info(cls, sandbox_id: str, **opts: Any) -> Any:  # type: ignore[no-redef]  # pylint: disable=function-redefined
        token, api_url = connection("AsyncSandbox.get_info", opts, cls._defaults)
        sandbox = await _DoSandbox.get(sandbox_id, token=token, api_url=api_url)
        try:
            return sandbox_info(await sandbox.get_info())
        finally:
            await sandbox.close()

    @by_id_or_self
    @translating
    async def create_snapshot(
        self, name: Optional[str] = None, *, mode: Optional[str] = None, **opts: Any
    ) -> Any:
        if mode is not None:
            raise SandboxNotImplementedError(
                "E2B.AsyncSandbox.create_snapshot(mode=...)", "a snapshot mode option"
            )
        snapshot = await self._do.create_snapshot(name=name)
        await snapshot.wait_until_ready()
        return snapshot_info(snapshot)

    @create_snapshot.by_id
    @translating
    async def create_snapshot(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        sandbox_id: str,
        name: Optional[str] = None,
        *,
        mode: Optional[str] = None,
        **opts: Any,
    ) -> Any:
        if mode is not None:
            raise SandboxNotImplementedError(
                "E2B.AsyncSandbox.create_snapshot(mode=...)", "a snapshot mode option"
            )
        token, api_url = connection("AsyncSandbox.create_snapshot", opts, cls._defaults)
        snapshot = await _DoSnapshot.create(
            sandbox_id, name=name, token=token, api_url=api_url
        )
        await snapshot.wait_until_ready()
        return snapshot_info(snapshot)

    @by_id_or_self
    @translating
    def list_snapshots(
        self,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        name: Optional[str] = None,
        **opts: Any,
    ) -> AsyncSnapshotPaginator:
        _no_name_filter(name)
        pages = _DoSnapshot.list(
            sandbox_id=self._do.sandbox_id,
            limit=limit,
            next_token=next_token,
            token=self._conn.get("token"),
            api_url=self._conn.get("api_url"),
        )
        return AsyncSnapshotPaginator(pages, limit, next_token)

    @list_snapshots.by_id
    @translating
    def list_snapshots(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        sandbox_id: Optional[str] = None,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        name: Optional[str] = None,
        **opts: Any,
    ) -> AsyncSnapshotPaginator:
        _no_name_filter(name)
        token, api_url = connection("AsyncSandbox.list_snapshots", opts, cls._defaults)
        pages = _DoSnapshot.list(
            sandbox_id=sandbox_id,
            limit=limit,
            next_token=next_token,
            token=token,
            api_url=api_url,
        )
        return AsyncSnapshotPaginator(pages, limit, next_token)

    @classmethod
    @translating
    async def delete_snapshot(cls, snapshot_id: str, **opts: Any) -> bool:
        token, api_url = connection("AsyncSandbox.delete_snapshot", opts, cls._defaults)
        return await _DoSnapshot.delete(snapshot_id, token=token, api_url=api_url)

    @classmethod
    @translating
    def list(
        cls,
        query: Optional[Any] = None,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        order: Optional[str] = None,
        **opts: Any,
    ) -> AsyncSandboxPaginator:
        no_list_options(order)
        state = state_filter(query)
        token, api_url = connection("AsyncSandbox.list", opts, cls._defaults)
        pages = _DoSandbox.list(
            state=state,
            limit=limit,
            next_token=next_token,
            token=token,
            api_url=api_url,
        )
        return AsyncSandboxPaginator(pages, limit, next_token)


def _check_connect(qualified: str, timeout: Optional[int], on_resume: str) -> None:
    reject_lifetime(qualified, timeout=timeout)
    if on_resume != "restore":
        raise SandboxNotImplementedError(
            "E2B.%s(on_resume=%r)" % (qualified, on_resume), "a reboot-on-resume option"
        )


def _no_name_filter(name: Optional[str]) -> None:
    if name is not None:
        raise SandboxNotImplementedError(
            "E2B.AsyncSandbox.list_snapshots(name=...)", "a snapshot name filter"
        )


__all__ = [
    "AsyncCommandHandle",
    "AsyncCommands",
    "AsyncSandbox",
    "AsyncSandboxPaginator",
    "AsyncSnapshotPaginator",
]
