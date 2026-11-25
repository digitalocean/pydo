# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Exec in a sandbox: ``/v2/sandboxes/{id}/exec``.

Hand-written; preserved across ``make generate``. The start call streams: the
request goes through the client's pipeline with ``stream=True``, so it keeps the
SDK's auth, retries and User-Agent. stdin and resize use the generated
operations.

Output arrives on the same request as the start, so there is no attach race:
prefer :meth:`Exec.run` over ``commands.run`` for short commands.

.. code-block:: python

    result = sandbox.exec.run("echo hello; exit 3")
    print(result.stdout, result.exit_code)

    with sandbox.exec.start(["cat"]) as session:
        session.write_stdin("hi\\n")
        session.close_stdin()
        print(session.wait().stdout)
"""

import codecs
import threading
from collections import deque
from typing import Any, Callable, Deque, Iterator, Mapping, Optional

from . import _exec as _e
from ._exec import Command, ExecEvent, ExecResult
from ._transport import call as _call, open_exec
from .errors import SandboxError, build_error


class Exec:
    """Runs processes in one sandbox and streams their output."""

    def __init__(self, client: Any, sandbox_id: str) -> None:
        self._client = client
        self._sandbox_id = sandbox_id

    def run(
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

        :keyword stdin: ``str`` or ``bytes`` sent as the process's stdin.
        """
        argv = _e.argv_for(command)
        body = _e.exec_body(argv, cwd, env_vars, timeout_seconds, False, None, stdin)
        session = ExecSession(self._client, self._sandbox_id, _open(self, body))
        try:
            return session.wait(on_stdout=on_stdout, on_stderr=on_stderr)
        finally:
            session.close()

    def start(
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

        :keyword keep_stdin_open: Keep stdin open for :meth:`ExecSession.write_stdin`
            (default ``True``).
        :keyword pty: ``True`` or a mapping of ``rows``, ``cols`` and ``term`` to
            run on a PTY. With a PTY, ``command`` may be omitted for the guest's
            default shell.
        """
        argv = _e.argv_for(command, pty=bool(pty) or pty == {})
        body = _e.exec_body(
            argv, cwd, env_vars, timeout_seconds, keep_stdin_open, pty, stdin
        )
        session = ExecSession(self._client, self._sandbox_id, _open(self, body))
        if body.get("keep_stdin_open") or "pty" in body:
            try:
                session._read_started()  # pylint: disable=protected-access
            except BaseException:
                session.close()
                raise
        return session


def _open(exec_: Exec, body: Any) -> Any:
    # pylint: disable=protected-access
    response = open_exec(exec_._client, exec_._sandbox_id, body)
    if response.status_code >= 400:
        try:
            response.read()
            try:
                parsed = response.json()
            except Exception:  # pylint: disable=broad-except
                parsed = None
            raise build_error(response.status_code, parsed, None, response.headers)
        finally:
            response.close()
    return response


class ExecSession:
    """A process started with :meth:`Exec.start`: read its output, write its stdin.

    Iterate it, or call :meth:`events`, for the output. There is one consumer.
    Use it as a context manager, or call :meth:`close`, to disconnect: the
    process may keep running.
    """

    def __init__(self, client: Any, sandbox_id: str, response: Any) -> None:
        self._client = client
        self._sandbox_id = sandbox_id
        self._response = response
        self._closed = False
        self._buffer: Deque[ExecEvent] = deque()
        self._source = self._read()
        self._offset = 0
        self._lock = threading.Lock()
        #: The exec ID, or ``None`` for a plain exec without stdin or PTY.
        self.exec_id: Optional[str] = None

    def __enter__(self) -> "ExecSession":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    def __iter__(self) -> Iterator[ExecEvent]:
        return self.events()

    def close(self) -> None:
        """Disconnects the stream. The process may keep running."""
        if not self._closed:
            self._closed = True
            self._response.close()

    def events(self) -> Iterator[ExecEvent]:
        """Yields the events as they happen.

        ``started`` (with stdin or PTY), ``stdout``, ``stderr`` and a final
        ``exit``. Keepalives are dropped. A stream that ends before an ``exit``
        event raises, because the outcome is unknown.
        """
        while self._buffer:
            yield self._buffer.popleft()
        yield from self._source

    def wait(
        self,
        *,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> ExecResult:
        """Consumes the stream until the process exits and returns its output."""
        text = _e.TextAssembler()
        try:
            for event in self.events():
                if event.type in ("stdout", "stderr"):
                    chunk = text.feed(event)  # type: ignore[arg-type]
                    callback = on_stdout if event.type == "stdout" else on_stderr
                    if chunk and callback:
                        callback(chunk)
                elif event.type == "exit":
                    return _e.result_from(event, text)
        finally:
            self.close()
        raise SandboxError("stopped waiting for the exec before it exited")

    def write_stdin(self, data: Any, *, eof: bool = False) -> None:
        """Writes ``str`` or ``bytes`` to stdin. ``eof=True`` closes it after.

        The byte offset is tracked for you and concurrent writes are serialized.
        """
        exec_id = self._require_id()
        raw = _e.to_bytes(data) if data else b""
        with self._lock:
            res = _call(
                self._client.sandboxes.post_exec_stdin,
                self._sandbox_id,
                exec_id,
                _e.stdin_body(raw, self._offset, eof),
            )
            self._offset = _e.next_offset(res, self._offset, len(raw))

    def close_stdin(self) -> None:
        """Closes stdin."""
        self.write_stdin(None, eof=True)

    def resize(self, rows: int, cols: int) -> None:
        """Resizes the PTY. ``rows`` and ``cols`` are 1 to 1000."""
        body = _e.resize_body(rows, cols)
        exec_id = self._require_id()
        _call(
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

    def _read_started(self) -> None:
        """Reads the first event, which carries the exec ID."""
        event = next(self._source, None)
        if event is None:  # pragma: no cover - _read raises first
            raise SandboxError(_e.STREAM_ENDED)
        if event.type == "started":
            self.exec_id = event.exec_id
        # Every early event is kept for the consumer, ``started`` included.
        self._buffer.append(event)

    def _read(self) -> Iterator[ExecEvent]:
        reader = _e.JsonObjectReader()
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        exited = False
        try:
            for chunk in self._response.iter_bytes():
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
            self.close()
