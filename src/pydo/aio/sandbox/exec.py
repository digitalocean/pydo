# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async exec in a sandbox: ``/v2/sandboxes/{id}/exec``.

Hand-written; preserved across ``make generate``. The async twin of
:mod:`pydo.sandbox.exec`: same names, with ``await`` and ``async for``. The
start call streams through the client's pipeline with ``stream=True``.

Output arrives on the same request as the start, so there is no attach race:
prefer :meth:`Exec.run` over ``commands.run`` for short commands.

.. code-block:: python

    result = await sandbox.exec.run("echo hello; exit 3")
    print(result.stdout, result.exit_code)

    async with await sandbox.exec.start(["cat"]) as session:
        await session.write_stdin("hi\\n")
        await session.close_stdin()
        print((await session.wait()).stdout)
"""

import asyncio
import codecs
from collections import deque
from typing import Any, AsyncIterator, Callable, Deque, Mapping, Optional, Union

from pydo.sandbox import _exec as _e
from pydo.sandbox._exec import Command, ExecEvent, ExecResult
from pydo.sandbox.errors import SandboxError, build_error

from ._transport import call as _call, open_exec


class Exec:
    """Runs processes in one sandbox and streams their output."""

    def __init__(self, client: Any, sandbox_id: str) -> None:
        self._client = client
        self._sandbox_id = sandbox_id

    async def __call__(
        self,
        command: Command,
        *,
        cwd: Optional[str] = None,
        env: Optional[Mapping[str, str]] = None,
        env_vars: Optional[Mapping[str, str]] = None,
        timeout: Union[int, str, None] = None,
        timeout_seconds: Optional[int] = None,
        check: bool = False,
        stdin: Any = None,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> ExecResult:
        """Runs a command and waits for it to exit: ``sandbox.exec("pytest -x")``.

        Like :meth:`run`, with ``env`` (alias of ``env_vars``) and ``timeout``
        (alias of ``timeout_seconds``: seconds, or ``"90s"``, ``"10m"``, ``"2h"``).
        A non-zero exit is returned; with ``check=True`` it raises
        :class:`~pydo.sandbox.CommandError`.
        """
        env_vars, timeout_seconds = _e.call_options(
            env, env_vars, timeout, timeout_seconds
        )
        result = await self.run(
            command,
            cwd=cwd,
            env_vars=env_vars,
            timeout_seconds=timeout_seconds,
            stdin=stdin,
            on_stdout=on_stdout,
            on_stderr=on_stderr,
        )
        return _e.check_result(result, check)

    async def run(
        self,
        command: Command,
        *,
        cwd: Optional[str] = None,
        env_vars: Optional[Mapping[str, str]] = None,
        timeout_seconds: Optional[int] = None,
        stdin: Any = None,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> ExecResult:
        """Runs a command and waits for it to exit.

        A string runs as ``bash -lc <command>``; a list is the argv. A non-zero
        exit code is returned in the result, not raised.
        """
        argv = _e.argv_for(command)
        body = _e.exec_body(argv, cwd, env_vars, timeout_seconds, False, None, stdin)
        session = ExecSession(self._client, self._sandbox_id, await _open(self, body))
        try:
            return await session.wait(on_stdout=on_stdout, on_stderr=on_stderr)
        finally:
            await session.close()

    async def start(
        self,
        command: Optional[Command] = None,
        *,
        cwd: Optional[str] = None,
        env_vars: Optional[Mapping[str, str]] = None,
        timeout_seconds: Optional[int] = None,
        stdin: Any = None,
        keep_stdin_open: bool = True,
        pty: Any = None,
    ) -> "ExecSession":
        """Starts a process for interactive use and returns its session.

        See :meth:`pydo.sandbox.exec.Exec.start`.
        """
        argv = _e.argv_for(command, pty=bool(pty) or pty == {})
        body = _e.exec_body(
            argv, cwd, env_vars, timeout_seconds, keep_stdin_open, pty, stdin
        )
        session = ExecSession(self._client, self._sandbox_id, await _open(self, body))
        if body.get("keep_stdin_open") or "pty" in body:
            try:
                await session._read_started()  # pylint: disable=protected-access
            except BaseException:
                await session.close()
                raise
        return session


async def _open(exec_: Exec, body: Any) -> Any:
    # pylint: disable=protected-access
    response = await open_exec(exec_._client, exec_._sandbox_id, body)
    if response.status_code >= 400:
        try:
            await response.read()
            try:
                parsed = response.json()
            except Exception:  # pylint: disable=broad-except
                parsed = None
            raise build_error(response.status_code, parsed, None, response.headers)
        finally:
            await response.close()
    return response


class ExecSession:
    """A process started with :meth:`Exec.start`: read its output, write its stdin.

    Use ``async for`` (or :meth:`events`) for the output. There is one consumer.
    Use it as an ``async with`` block, or await :meth:`close`, to disconnect:
    the process may keep running.
    """

    def __init__(self, client: Any, sandbox_id: str, response: Any) -> None:
        self._client = client
        self._sandbox_id = sandbox_id
        self._response = response
        self._closed = False
        self._buffer: Deque[ExecEvent] = deque()
        self._source = self._read()
        self._offset = 0
        self._lock = asyncio.Lock()
        #: The exec ID, or ``None`` for a plain exec without stdin or PTY.
        self.exec_id: Optional[str] = None

    async def __aenter__(self) -> "ExecSession":
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self.close()

    def __aiter__(self) -> AsyncIterator[ExecEvent]:
        return self.events()

    async def close(self) -> None:
        """Disconnects the stream. The process may keep running."""
        if not self._closed:
            self._closed = True
            await self._response.close()

    async def events(self) -> AsyncIterator[ExecEvent]:
        """Yields the events as they happen (``async for``).

        ``started`` (with stdin or PTY), ``stdout``, ``stderr`` and a final
        ``exit``. A stream that ends before an ``exit`` event raises, because
        the outcome is unknown.
        """
        while self._buffer:
            yield self._buffer.popleft()
        async for event in self._source:
            yield event

    async def wait(
        self,
        *,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> ExecResult:
        """Consumes the stream until the process exits and returns its output."""
        text = _e.TextAssembler()
        events = self.events()
        try:
            async for event in events:
                if event.type in ("stdout", "stderr"):
                    chunk = text.feed(event)  # type: ignore[arg-type]
                    callback = on_stdout if event.type == "stdout" else on_stderr
                    if chunk and callback:
                        callback(chunk)
                elif event.type == "exit":
                    return _e.result_from(event, text)
        finally:
            await events.aclose()
            await self.close()
        raise SandboxError("stopped waiting for the exec before it exited")

    async def write_stdin(self, data: Any, *, eof: bool = False) -> None:
        """Writes ``str`` or ``bytes`` to stdin. ``eof=True`` closes it after.

        The byte offset is tracked for you and concurrent writes are serialized.
        """
        exec_id = self._require_id()
        raw = _e.to_bytes(data) if data else b""
        async with self._lock:
            res = await _call(
                self._client.sandboxes.post_exec_stdin,
                self._sandbox_id,
                exec_id,
                _e.stdin_body(raw, self._offset, eof),
            )
            self._offset = _e.next_offset(res, self._offset, len(raw))

    async def close_stdin(self) -> None:
        """Closes stdin."""
        await self.write_stdin(None, eof=True)

    async def resize(self, rows: int, cols: int) -> None:
        """Resizes the PTY. ``rows`` and ``cols`` are 1 to 1000."""
        body = _e.resize_body(rows, cols)
        exec_id = self._require_id()
        await _call(
            self._client.sandboxes.post_exec_resize,
            self._sandbox_id,
            exec_id,
            body,
        )

    def _require_id(self) -> str:
        if not self.exec_id:
            raise SandboxError(
                "this exec has no ID: start it with keep_stdin_open or a pty"
            )
        return self.exec_id

    async def _read_started(self) -> None:
        """Reads the first event, which carries the exec ID."""
        event = await self._source.__anext__()
        if event.type == "started":
            self.exec_id = event.exec_id
        # Every early event is kept for the consumer, ``started`` included.
        self._buffer.append(event)

    async def _read(self) -> AsyncIterator[ExecEvent]:
        reader = _e.JsonObjectReader()
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        exited = False
        try:
            async for chunk in self._response.iter_bytes():
                for raw in reader.push(decoder.decode(chunk)):
                    event = _e.to_exec_event(raw)
                    if event is None:
                        continue
                    yield event
                    if event.type == "exit":
                        exited = True
                        return
            if not exited and not self._closed:
                raise SandboxError(_e.STREAM_ENDED)
        finally:
            await self.close()
