# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Modal's ``Sandbox`` (modal 1.6.4) over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. Modal wraps one coroutine in a
blocking call and an ``.aio`` call; the same two spellings work here.
``Sandbox.create(...)`` runs on the synchronous Sandboxes SDK and ``await
Sandbox.create.aio(...)`` on the asynchronous one (``pydo.aio``, imported on first
use). A sandbox keeps the backend it was created with: call its blocking methods
or its ``.aio`` methods accordingly.

What works: ``create`` (``cpu``/``memory`` round up to a size, ``env``, ``secrets``
from ``Secret.from_dict``, ``block_network``, ``workdir``, ``image`` from
``Image.debian_slim()`` or ``Image.from_registry(...)``, an entrypoint),
``exec`` with ``stdout``/``stderr``/``stdin``, ``wait``, ``poll``, ``terminate``,
``from_id``, ``list``, pause and resume. Everything else keeps Modal's signature
and raises :class:`~pydo.sandbox.errors.SandboxNotImplementedError`.
"""

import asyncio
import inspect
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Tuple

from ... import Sandbox as _DoSandbox
from ...errors import NotFoundError as _NotFound
from ...errors import SandboxError
from ...templates import Template as _DoTemplate
from .._base import ModalMethod, translating, with_signature
from . import _mirror as _m
from ._common import Image, create_plan, process_options, size_for
from .exceptions import Error, map_error


class _Mapped:
    @staticmethod
    def _map_error(err: SandboxError) -> BaseException:
        return map_error(err)


def _wrong_backend(kind: str) -> Error:
    other = "its .aio() methods" if kind == "sync" else "its blocking methods"
    return Error("this object was created with the %s API: use %s" % (kind, other))


class _Pump:
    """One command's event stream, split into stdout and stderr buffers.

    Reading either stream advances the shared stream, so stdout and stderr can be
    read in any order without losing output.
    """

    def __init__(self, command: Any, text: bool, backend: str) -> None:
        self.command = command
        self.text = text
        self.backend = backend
        self.chunks: Dict[int, List[Any]] = {1: [], 2: []}
        self.read_upto: Dict[int, int] = {1: 0, 2: 0}
        self.done = False
        self.returncode: Optional[int] = None
        self._events = command.stream()

    def _take(self, event: Any) -> None:
        if event.type == "stdout":
            self.chunks[1].append(event.text if self.text else event.data)
        elif event.type == "stderr":
            self.chunks[2].append(event.text if self.text else event.data)
        elif event.type == "exit":
            self.returncode = event.exit_code
            self.done = True

    def advance(self) -> bool:
        """Read one more event (blocking). ``False`` once the command has exited."""
        if self.done:
            return False
        try:
            self._take(next(self._events))
        except StopIteration:
            self.done = True
        return not self.done

    async def aadvance(self) -> bool:
        if self.done:
            return False
        try:
            self._take(await self._events.__anext__())
        except StopAsyncIteration:
            self.done = True
        return not self.done

    def join(self, fd: int) -> Any:
        items = self.chunks[fd][self.read_upto[fd] :]
        self.read_upto[fd] = len(self.chunks[fd])
        return "".join(items) if self.text else b"".join(items)


class StreamReader(_Mapped, _m.StreamReader):
    """``process.stdout`` / ``process.stderr``: ``read()`` and iteration."""

    def __init__(
        self, pump: _Pump, fd: int
    ) -> None:  # pylint: disable=super-init-not-called
        self._pump = pump
        self._fd = fd
        self._closed = False

    @property
    def file_descriptor(self) -> int:
        return self._fd

    def _sync(self) -> _Pump:
        if self._pump.backend != "sync":
            raise _wrong_backend("async")
        return self._pump

    @translating
    def _read_sync(self) -> Any:
        pump = self._sync()
        while pump.advance():
            pass
        return pump.join(self._fd)

    @translating
    async def _read_aio(self) -> Any:
        pump = self._pump
        if pump.backend == "sync":
            return await asyncio.to_thread(self._read_sync)
        while await pump.aadvance():
            pass
        return pump.join(self._fd)

    read = ModalMethod(_read_sync, _read_aio, "method")

    def __iter__(self) -> Iterator[Any]:
        pump = self._sync()
        nl = "\n" if pump.text else b"\n"
        buffer = pump.join(self._fd)
        while True:
            while nl in buffer:
                line, buffer = buffer.split(nl, 1)
                yield line + nl
            if not pump.advance():
                buffer += pump.join(self._fd)
                break
            buffer += pump.join(self._fd)
        while nl in buffer:
            line, buffer = buffer.split(nl, 1)
            yield line + nl
        if buffer:
            yield buffer

    async def __aiter__(self) -> AsyncIterator[Any]:
        pump = self._pump
        nl = "\n" if pump.text else b"\n"
        buffer = pump.join(self._fd)
        while True:
            while nl in buffer:
                line, buffer = buffer.split(nl, 1)
                yield line + nl
            if not await pump.aadvance():
                buffer += pump.join(self._fd)
                break
            buffer += pump.join(self._fd)
        while nl in buffer:
            line, buffer = buffer.split(nl, 1)
            yield line + nl
        if buffer:
            yield buffer

    def close(self) -> None:
        self._closed = True

    async def aclose(self) -> None:
        self._closed = True


class StreamWriter(_Mapped, _m.StreamWriter):
    """``process.stdin``: buffer with ``write``, send with ``drain``, end with ``write_eof``."""

    def __init__(
        self, command: Any, backend: str
    ) -> None:  # pylint: disable=super-init-not-called
        self._command = command
        self._backend = backend
        self._buffer = bytearray()
        self._eof = False

    def _write_impl(self, data: Any) -> None:
        if self._eof:
            raise ValueError("stdin is closed")
        self._buffer += data.encode() if isinstance(data, str) else bytes(data)

    async def _write_aio(self, data: Any) -> None:
        self._write_impl(data)

    write = ModalMethod(
        lambda self, data: self._write_impl(data),
        lambda self, data: self._write_aio(data),
        "method",
    )

    @translating
    def _write_eof_sync(self) -> None:
        self._drain_sync()
        self._eof = True
        self._command.close_stdin()

    @translating
    async def _write_eof_aio(self) -> None:
        await self._drain_aio()
        self._eof = True
        await self._command.close_stdin()

    write_eof = ModalMethod(_write_eof_sync, _write_eof_aio, "method")

    @translating
    def _drain_sync(self) -> None:
        if self._backend != "sync":
            raise _wrong_backend("async")
        if self._buffer:
            data, self._buffer = bytes(self._buffer), bytearray()
            self._command.write_stdin(data)

    @translating
    async def _drain_aio(self) -> None:
        if self._backend == "sync":
            await asyncio.to_thread(self._drain_sync)
            return
        if self._buffer:
            data, self._buffer = bytes(self._buffer), bytearray()
            await self._command.write_stdin(data)

    drain = ModalMethod(_drain_sync, _drain_aio, "method")


class ContainerProcess(_Mapped, _m.ContainerProcess):
    """A command started with ``sandbox.exec(...)``."""

    def __init__(
        self, command: Any, text: bool, backend: str
    ) -> None:  # pylint: disable=super-init-not-called
        self._command = command
        self._pump = _Pump(command, text, backend)
        self._stdout = StreamReader(self._pump, 1)
        self._stderr = StreamReader(self._pump, 2)
        self._stdin = StreamWriter(command, backend)

    @property
    def stdout(self) -> StreamReader:
        return self._stdout

    @property
    def stderr(self) -> StreamReader:
        return self._stderr

    @property
    def stdin(self) -> StreamWriter:
        return self._stdin

    @property
    def returncode(self) -> Optional[int]:
        return self._pump.returncode

    def _poll_sync(self) -> Optional[int]:
        return self._pump.returncode

    async def _poll_aio(self) -> Optional[int]:
        return self._pump.returncode

    poll = ModalMethod(_poll_sync, _poll_aio, "method")

    @translating
    def _wait_sync(self) -> int:
        if self._pump.backend != "sync":
            raise _wrong_backend("async")
        while self._pump.advance():
            pass
        return self._pump.returncode if self._pump.returncode is not None else 0

    @translating
    async def _wait_aio(self) -> int:
        if self._pump.backend == "sync":
            return await asyncio.to_thread(self._wait_sync)
        while await self._pump.aadvance():
            pass
        return self._pump.returncode if self._pump.returncode is not None else 0

    wait = ModalMethod(_wait_sync, _wait_aio, "method")


def _ensure_template(image: Optional[Image], conn: Dict[str, Any]) -> Optional[str]:
    """The template a registry image is built into (created once, then reused by name)."""
    name = image.template_name() if image is not None else None
    if name is None:
        return None
    pages = _DoTemplate.list(**conn)
    while pages.has_next:
        for template in pages.next_items():
            if template.name == name:
                template.wait_until_ready()
                return name
    _DoTemplate.create(
        name=name, source_oci_ref=image._oci_ref, **conn
    ).wait_until_ready()  # pylint: disable=protected-access
    return name


async def _ensure_template_aio(
    image: Optional[Image], conn: Dict[str, Any]
) -> Optional[str]:
    from pydo.aio.sandbox.templates import (
        Template as AioTemplate,
    )  # pylint: disable=import-outside-toplevel

    name = image.template_name() if image is not None else None
    if name is None:
        return None
    pages = AioTemplate.list(**conn)
    while pages.has_next:
        for template in await pages.next_items():
            if template.name == name:
                await template.wait_until_ready()
                return name
    created = await AioTemplate.create(
        name=name, source_oci_ref=image._oci_ref, **conn
    )  # pylint: disable=protected-access
    await created.wait_until_ready()
    return name


class Sandbox(_Mapped, _m.Sandbox):
    """Modal's ``Sandbox``, backed by a DigitalOcean Sandbox."""

    #: Token and API origin a bound client fills in (see ``ModalClient``).
    _defaults: Dict[str, Any] = {}

    def __init__(
        self,
        _do: Any = None,
        _conn: Optional[Dict[str, Any]] = None,
        _backend: str = "sync",
        _entry: Optional[ContainerProcess] = None,
        _workdir: Optional[str] = None,
    ) -> None:  # pylint: disable=super-init-not-called
        if _do is None:
            raise Error("Sandbox() cannot be called directly: use Sandbox.create()")
        self._do = _do
        self._conn = _conn or {}
        self._backend = _backend
        self._entry = _entry
        self._workdir = _workdir

    @property
    def object_id(self) -> str:
        return self._do.sandbox_id

    @property
    def stdout(self) -> StreamReader:
        return self._entrypoint().stdout

    @property
    def stderr(self) -> StreamReader:
        return self._entrypoint().stderr

    @property
    def stdin(self) -> StreamWriter:
        return self._entrypoint().stdin

    @property
    def returncode(self) -> Optional[int]:
        return self._entry.returncode if self._entry else None

    @property
    def filesystem(self) -> _m.SandboxFilesystem:
        return self._child(_m.SandboxFilesystem)

    def _entrypoint(self) -> ContainerProcess:
        if self._entry is None:
            raise Error(
                "this Sandbox was created without an entrypoint command: use sandbox.exec(...)"
            )
        return self._entry

    # -- create --------------------------------------------------------------

    @with_signature(_m.Sandbox._create_sync)
    @translating
    def _create_sync(cls, a: Dict[str, Any]) -> "Sandbox":  # type: ignore[misc]  # pylint: disable=no-self-argument
        plan = create_plan(a)
        client = a.get("client")
        conn = _conn_of(cls, client)
        template = _ensure_template(plan["image"], conn)
        sandbox = _DoSandbox.create(
            template=template,
            size=size_for(plan["cpu"], plan["memory"], cls._defaults.get("size")),
            allow_internet_access=plan["allow_internet_access"],
            env_vars=plan["env_vars"],
            **conn,
        )
        entry = None
        if plan["entrypoint"]:
            exe, *rest = plan["entrypoint"]
            command = sandbox.commands.start(
                exe, args=rest, cwd=plan["workdir"], stdin=True
            )
            entry = ContainerProcess(command, True, "sync")
        return cls(sandbox, conn, "sync", entry, plan["workdir"])

    @with_signature(_m.Sandbox._create_sync)
    @translating
    async def _create_aio(cls, a: Dict[str, Any]) -> "Sandbox":  # type: ignore[misc]  # pylint: disable=no-self-argument
        from pydo.aio.sandbox.sandbox import (
            Sandbox as AioSandbox,
        )  # pylint: disable=import-outside-toplevel

        plan = create_plan(a)
        conn = _conn_of(cls, a.get("client"))
        template = await _ensure_template_aio(plan["image"], conn)
        sandbox = await AioSandbox.create(
            template=template,
            size=size_for(plan["cpu"], plan["memory"], cls._defaults.get("size")),
            allow_internet_access=plan["allow_internet_access"],
            env_vars=plan["env_vars"],
            **conn,
        )
        entry = None
        if plan["entrypoint"]:
            exe, *rest = plan["entrypoint"]
            command = await sandbox.commands.start(
                exe, args=rest, cwd=plan["workdir"], stdin=True
            )
            entry = ContainerProcess(command, True, "async")
        return cls(sandbox, conn, "async", entry, plan["workdir"])

    create = ModalMethod(_create_sync, _create_aio, "classmethod")

    # -- find ----------------------------------------------------------------

    @translating
    def _from_id_sync(cls, sandbox_id: str, client: Optional[Any] = None) -> "Sandbox":  # type: ignore[misc]  # pylint: disable=no-self-argument
        conn = _conn_of(cls, client)
        return cls(_DoSandbox.get(sandbox_id, **conn), conn, "sync")

    @translating
    async def _from_id_aio(cls, sandbox_id: str, client: Optional[Any] = None) -> "Sandbox":  # type: ignore[misc]  # pylint: disable=no-self-argument
        from pydo.aio.sandbox.sandbox import (
            Sandbox as AioSandbox,
        )  # pylint: disable=import-outside-toplevel

        conn = _conn_of(cls, client)
        return cls(await AioSandbox.get(sandbox_id, **conn), conn, "async")

    from_id = ModalMethod(_from_id_sync, _from_id_aio, "classmethod")

    def _list_sync(cls, *, app_id: Optional[str] = None, tags: Optional[Dict[str, str]] = None, client: Optional[Any] = None) -> Iterator["Sandbox"]:  # type: ignore[misc]  # pylint: disable=no-self-argument
        _no_filters(app_id, tags)
        conn = _conn_of(cls, client)
        try:
            pages = _DoSandbox.list(**conn)
            while pages.has_next:
                for do in pages.next_items():
                    yield cls(do, conn, "sync")
        except SandboxError as err:
            raise map_error(err) from err

    async def _list_aio(cls, *, app_id: Optional[str] = None, tags: Optional[Dict[str, str]] = None, client: Optional[Any] = None) -> AsyncIterator["Sandbox"]:  # type: ignore[misc]  # pylint: disable=no-self-argument
        from pydo.aio.sandbox.sandbox import (
            Sandbox as AioSandbox,
        )  # pylint: disable=import-outside-toplevel

        _no_filters(app_id, tags)
        conn = _conn_of(cls, client)
        pages = AioSandbox.list(**conn)
        try:
            while pages.has_next:
                for do in await pages.next_items():
                    yield cls(do, conn, "async")
        except SandboxError as err:
            raise map_error(err) from err

    list = ModalMethod(_list_sync, _list_aio, "classmethod")

    # -- run commands ----------------------------------------------------------

    @with_signature(_m.Sandbox._exec_sync)
    @translating
    def _exec_sync(self, a: Dict[str, Any]) -> ContainerProcess:  # type: ignore[misc]
        self._require("sync")
        exe, args, cwd, env, seconds, text = _exec_args(self, a)
        command = self._do.commands.start(
            exe,
            args=args,
            cwd=cwd,
            env_vars=env or None,
            stdin=True,
            timeout_seconds=seconds,
        )
        return ContainerProcess(command, text, "sync")

    @with_signature(_m.Sandbox._exec_sync)
    @translating
    async def _exec_aio(self, a: Dict[str, Any]) -> ContainerProcess:  # type: ignore[misc]
        if self._backend == "sync":
            return await asyncio.to_thread(
                self._exec_sync,
                *a["args"],
                **{k: v for k, v in a.items() if k != "args"},
            )
        exe, args, cwd, env, seconds, text = _exec_args(self, a)
        command = await self._do.commands.start(
            exe,
            args=args,
            cwd=cwd,
            env_vars=env or None,
            stdin=True,
            timeout_seconds=seconds,
        )
        return ContainerProcess(command, text, "async")

    exec = ModalMethod(_exec_sync, _exec_aio, "method")

    # -- lifecycle ---------------------------------------------------------------

    def _require(self, backend: str) -> None:
        if self._backend != backend:
            raise _wrong_backend(self._backend)

    @translating
    def _terminate_sync(self, *, wait: bool = False) -> Optional[int]:
        self._require("sync")
        self._do.kill()
        return self.returncode if wait else None

    @translating
    async def _terminate_aio(self, *, wait: bool = False) -> Optional[int]:
        if self._backend == "sync":
            return await asyncio.to_thread(self._terminate_sync, wait=wait)
        await self._do.kill()
        return self.returncode if wait else None

    terminate = ModalMethod(_terminate_sync, _terminate_aio, "method")

    @translating
    def _wait_sync(self, raise_on_termination: bool = True) -> None:
        self._require("sync")
        if self._entry is not None:
            self._entry.wait()
            return
        while True:
            try:
                self._do.get_info()
            except _NotFound:
                return
            import time  # pylint: disable=import-outside-toplevel

            time.sleep(1.0)

    @translating
    async def _wait_aio(self, raise_on_termination: bool = True) -> None:
        if self._backend == "sync":
            await asyncio.to_thread(self._wait_sync, raise_on_termination)
            return
        if self._entry is not None:
            await self._entry.wait.aio()
            return
        while True:
            try:
                await self._do.get_info()
            except _NotFound:
                return
            await asyncio.sleep(1.0)

    wait = ModalMethod(_wait_sync, _wait_aio, "method")

    def _poll_sync(self) -> Optional[int]:
        return self.returncode

    async def _poll_aio(self) -> Optional[int]:
        return self.returncode

    poll = ModalMethod(_poll_sync, _poll_aio, "method")

    def _detach_sync(self) -> None:
        if self._backend == "sync":
            self._do.close()

    async def _detach_aio(self) -> None:
        if self._backend == "sync":
            self._do.close()
        else:
            await self._do.close()

    detach = ModalMethod(_detach_sync, _detach_aio, "method")

    @translating
    def _wait_until_ready_sync(self, *, timeout: int = 300) -> None:
        self._require("sync")
        self._do.wait_until_running(timeout=timeout)

    @translating
    async def _wait_until_ready_aio(self, *, timeout: int = 300) -> None:
        if self._backend == "sync":
            await asyncio.to_thread(self._wait_until_ready_sync, timeout=timeout)
            return
        await self._do.wait_until_running(timeout=timeout)

    wait_until_ready = ModalMethod(
        _wait_until_ready_sync, _wait_until_ready_aio, "method"
    )

    @translating
    def _experimental_pause_sync(self) -> None:
        self._require("sync")
        self._do.pause()

    @translating
    async def _experimental_pause_aio(self) -> None:
        if self._backend == "sync":
            await asyncio.to_thread(self._experimental_pause_sync)
            return
        await self._do.pause()

    _experimental_pause = ModalMethod(
        _experimental_pause_sync, _experimental_pause_aio, "method"
    )

    @translating
    def _experimental_resume_sync(self) -> None:
        self._require("sync")
        self._do.resume()

    @translating
    async def _experimental_resume_aio(self) -> None:
        if self._backend == "sync":
            await asyncio.to_thread(self._experimental_resume_sync)
            return
        await self._do.resume()

    _experimental_resume = ModalMethod(
        _experimental_resume_sync, _experimental_resume_aio, "method"
    )


def _conn_of(cls: Any, client: Optional[Any]) -> Dict[str, Any]:
    defaults = dict(getattr(client, "_conn", None) or cls._defaults)
    return {"token": defaults.get("token"), "api_url": defaults.get("api_url")}


def _no_filters(app_id: Optional[str], tags: Optional[Dict[str, str]]) -> None:
    from .. import _base  # pylint: disable=import-outside-toplevel

    _base.reject(
        "modal",
        "Sandbox.list",
        "listing sandboxes by app or tags",
        app_id=app_id,
        tags=tags,
    )


def _exec_args(
    box: Sandbox, a: Dict[str, Any]
) -> Tuple[str, List[str], Optional[str], Dict[str, str], Optional[int], bool]:
    workdir, env, timeout = process_options("Sandbox.exec", a)
    args = tuple(a.get("args") or ())
    if not args:
        raise Error("exec: pass the command to run, such as sandbox.exec('echo', 'hi')")
    return (
        args[0],
        list(args[1:]),
        workdir or box._workdir,
        env,
        timeout,
        bool(a.get("text", True)),
    )  # pylint: disable=protected-access


__all__ = ["ContainerProcess", "Sandbox", "StreamReader", "StreamWriter"]
