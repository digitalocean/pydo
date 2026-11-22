# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async commands running in a sandbox: ``/v2/sandboxes/{id}/commands``.

Hand-written; preserved across ``make generate``. The async twin of
:mod:`pydo.sandbox.commands`: same names, with ``await`` and ``async for``.

.. code-block:: python

    result = await sandbox.commands.run('echo "Hello"')
    print(result.stdout, result.exit_code)
"""

from typing import Any, AsyncIterator, Callable, List, Mapping, Optional

from pydo.sandbox import _commands as _c
from pydo.sandbox._commands import CommandEvent, CommandInfo, CommandResult
from pydo.sandbox.errors import NotFoundError, SandboxError, build_error

from ._transport import call as _call, open_stream


class Commands:
    """Starts commands in one sandbox and finds the ones already running."""

    def __init__(self, client: Any, sandbox_id: str) -> None:
        self._client = client
        self._sandbox_id = sandbox_id

    async def start(
        self,
        cmd: str,
        *,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        env_vars: Optional[Mapping[str, str]] = None,
        stdin: bool = False,
        timeout_seconds: Optional[int] = None,
    ) -> "Command":
        """Starts an executable and returns once it is running. See :meth:`pydo.sandbox.commands.Commands.start`."""
        body = _c.start_body(cmd, args, cwd, env_vars, stdin, timeout_seconds)
        res = await _call(self._client.sandboxes.create_command, self._sandbox_id, body)
        pid = (res or {}).get("pid")
        if pid is None:
            raise SandboxError("the API response did not include the command's pid")
        return Command(self._client, self._sandbox_id, int(pid))

    async def run(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        env_vars: Optional[Mapping[str, str]] = None,
        timeout_seconds: Optional[int] = None,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """Runs a shell command (``bash -lc <command>``) and waits for it to exit.

        A non-zero exit code is returned in the result, not raised.
        """
        cmd = await self.start(
            "bash",
            args=["-lc", command],
            cwd=cwd,
            env_vars=env_vars,
            timeout_seconds=timeout_seconds,
        )
        return await cmd.wait(on_stdout=on_stdout, on_stderr=on_stderr)

    async def list(self) -> List[CommandInfo]:
        """Lists the commands that are running."""
        res = await _call(self._client.sandboxes.list_commands, self._sandbox_id) or {}
        return [
            CommandInfo(pid=int(c["pid"]), cmd=c.get("cmd") or "", cwd=c.get("cwd"))
            for c in res.get("commands") or []
        ]

    def connect(self, pid: int) -> "Command":
        """A handle on a command that is already running. Makes no request."""
        return Command(self._client, self._sandbox_id, pid)


class Command:
    """A command in a sandbox: read its output, write its stdin, stop it."""

    def __init__(self, client: Any, sandbox_id: str, pid: int) -> None:
        self._client = client
        self._sandbox_id = sandbox_id
        #: The process ID of the command.
        self.pid = pid

    async def stream(self) -> AsyncIterator[CommandEvent]:
        """Yields the command's events as they happen (``async for``).

        ``started``, ``stdout``, ``stderr`` and a final ``exit``. A stream that
        ends before an ``exit`` event raises, because the outcome is unknown.
        """
        exited = False
        attach = self._attach()
        try:
            async for event in attach:
                yield event
                if event.type == "exit":
                    exited = True
        finally:
            await attach.aclose()
        if not exited:
            raise SandboxError(
                "the stream for command %d ended before the command exited; "
                "its outcome is unknown" % self.pid
            )

    async def wait(
        self,
        *,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """Waits for the command to exit and returns its output and exit code."""
        text = _c.TextAssembler()
        events = self.stream()
        try:
            async for event in events:
                if event.type in ("stdout", "stderr"):
                    chunk = text.feed(event)
                    callback = on_stdout if event.type == "stdout" else on_stderr
                    if chunk and callback:
                        callback(chunk)
                elif event.type == "exit":
                    text.finish()
                    return CommandResult(
                        pid=self.pid,
                        exit_code=event.exit_code or 0,
                        stdout=text.stdout,
                        stderr=text.stderr,
                        status=event.status,
                        error=event.error,
                    )
        finally:
            # Closing the generator closes the response; leaving it suspended
            # would hold the connection until garbage collection.
            await events.aclose()
        raise SandboxError("stopped waiting for command %d before it exited" % self.pid)

    async def kill(self, signal: str = "SIGTERM") -> None:
        """Sends a signal to the command: ``SIGTERM`` (default) or ``SIGKILL``."""
        value = _c.signal_value(signal)
        await _call(
            self._client.sandboxes.post_commands_signal,
            self._sandbox_id,
            self.pid,
            {"signal": value},
        )

    async def write_stdin(self, data: Any, *, eof: bool = False) -> None:
        """Writes ``str`` or ``bytes`` to the command's stdin (started with ``stdin=True``)."""
        await _call(
            self._client.sandboxes.post_commands_stdin,
            self._sandbox_id,
            self.pid,
            _c.stdin_body(data, eof),
        )

    async def close_stdin(self) -> None:
        """Closes the command's stdin."""
        await self.write_stdin(None, eof=True)

    async def _attach(self) -> AsyncIterator[CommandEvent]:
        response = await open_stream(self._client, self._sandbox_id, self.pid)
        reader = _c.JsonObjectReader()
        decoder = _c.codecs.getincrementaldecoder("utf-8")("replace")
        try:
            if response.status_code >= 400:
                await response.read()
                try:
                    body = response.json()
                except Exception:  # pylint: disable=broad-except
                    body = None
                err = build_error(response.status_code, body, None, response.headers)
                if isinstance(err, NotFoundError):
                    raise NotFoundError(
                        "command %d not found or already exited: output can only be read while it runs"
                        % self.pid,
                        status=err.status,
                        code=err.code,
                        request_id=err.request_id,
                    )
                raise err
            async for chunk in response.iter_bytes():
                for raw in reader.push(decoder.decode(chunk)):
                    event = _c.to_event(raw)
                    if event is not None:
                        yield event
        finally:
            await response.close()
