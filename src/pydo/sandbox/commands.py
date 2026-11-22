# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Commands running in a sandbox: ``/v2/sandboxes/{id}/commands``.

Hand-written; preserved across ``make generate``. JSON calls go through the
generated ``client.sandboxes`` operations. The attach stream reads the same
generated request through the client's pipeline with ``stream=True``, so it
keeps the SDK's auth, retries and User-Agent.

.. code-block:: python

    result = sandbox.commands.run('echo "Hello"')
    print(result.stdout, result.exit_code)

    cmd = sandbox.commands.start("sleep", args=["60"])
    cmd.kill()
"""

from typing import Any, Callable, Iterator, List, Mapping, Optional

from . import _commands as _c
from .errors import NotFoundError, SandboxError, build_error
from ._transport import call as _call, open_stream
from ._commands import CommandEvent, CommandInfo, CommandResult


class Commands:
    """Starts commands in one sandbox and finds the ones already running."""

    def __init__(self, client: Any, sandbox_id: str) -> None:
        self._client = client
        self._sandbox_id = sandbox_id

    def start(
        self,
        cmd: str,
        *,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        env_vars: Optional[Mapping[str, str]] = None,
        stdin: bool = False,
        timeout_seconds: Optional[int] = None,
    ) -> "Command":
        """Starts an executable and returns once it is running.

        It keeps running after this call returns. For a shell string use
        :meth:`run`, or pass ``"bash"`` with ``args=["-lc", "..."]``.

        :keyword stdin: Leave stdin open, so :meth:`Command.write_stdin` can write to it.
        :keyword timeout_seconds: Kill the command after this long. Omit or 0 for no timeout.
        """
        body = _c.start_body(cmd, args, cwd, env_vars, stdin, timeout_seconds)
        res = _call(self._client.sandboxes.create_command, self._sandbox_id, body)
        pid = (res or {}).get("pid")
        if pid is None:
            raise SandboxError("the API response did not include the command's pid")
        return Command(self._client, self._sandbox_id, int(pid))

    def run(
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

        A non-zero exit code is returned in the result, not raised. Output can
        only be read while the command runs, so a command that exits before the
        stream attaches raises :class:`NotFoundError`.
        """
        cmd = self.start(
            "bash",
            args=["-lc", command],
            cwd=cwd,
            env_vars=env_vars,
            timeout_seconds=timeout_seconds,
        )
        return cmd.wait(on_stdout=on_stdout, on_stderr=on_stderr)

    def list(self) -> List[CommandInfo]:
        """Lists the commands that are running."""
        res = _call(self._client.sandboxes.list_commands, self._sandbox_id) or {}
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

    def stream(self) -> Iterator[CommandEvent]:
        """Yields the command's events as they happen.

        ``started``, ``stdout``, ``stderr`` and a final ``exit``. Keepalives are
        dropped. Leave the loop to disconnect; the command keeps running. A
        stream that ends before an ``exit`` event raises, because the outcome is
        unknown.
        """
        exited = False
        attach = self._attach()
        try:
            for event in attach:
                yield event
                if event.type == "exit":
                    exited = True
        finally:
            attach.close()
        if not exited:
            raise SandboxError(
                "the stream for command %d ended before the command exited; "
                "its outcome is unknown" % self.pid
            )

    def wait(
        self,
        *,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """Waits for the command to exit and returns its output and exit code."""
        text = _c.TextAssembler()
        events = self.stream()
        try:
            for event in events:
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
            # Closing the generator closes the response promptly.
            events.close()
        raise SandboxError("stopped waiting for command %d before it exited" % self.pid)

    def kill(self, signal: str = "SIGTERM") -> None:
        """Sends a signal to the command: ``SIGTERM`` (default) or ``SIGKILL``."""
        value = _c.signal_value(signal)
        _call(
            self._client.sandboxes.post_commands_signal,
            self._sandbox_id,
            self.pid,
            {"signal": value},
        )

    def write_stdin(self, data: Any, *, eof: bool = False) -> None:
        """Writes ``str`` or ``bytes`` to the command's stdin.

        The command must have been started with ``stdin=True``. Pass
        ``eof=True`` to close stdin after writing.
        """
        _call(
            self._client.sandboxes.post_commands_stdin,
            self._sandbox_id,
            self.pid,
            _c.stdin_body(data, eof),
        )

    def close_stdin(self) -> None:
        """Closes the command's stdin."""
        self.write_stdin(None, eof=True)

    def _attach(self) -> Iterator[CommandEvent]:
        # pylint: disable=protected-access
        response = open_stream(self._client, self._sandbox_id, self.pid)
        reader = _c.JsonObjectReader()
        decoder = _c.codecs.getincrementaldecoder("utf-8")("replace")
        try:
            if response.status_code >= 400:
                response.read()
                err = build_error(
                    response.status_code,
                    _json_or_none(response),
                    None,
                    response.headers,
                )
                if isinstance(err, NotFoundError):
                    raise NotFoundError(
                        "command %d not found or already exited: output can only be read while it runs"
                        % self.pid,
                        status=err.status,
                        code=err.code,
                        request_id=err.request_id,
                    )
                raise err
            for chunk in response.iter_bytes():
                for raw in reader.push(decoder.decode(chunk)):
                    event = _c.to_event(raw)
                    if event is not None:
                        yield event
        finally:
            response.close()


def _json_or_none(response: Any) -> Any:
    try:
        return response.json()
    except Exception:  # pylint: disable=broad-except
        return None
