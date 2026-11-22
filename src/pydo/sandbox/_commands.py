# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Types and helpers shared by the sync and async sandbox commands.

Hand-written; preserved across ``make generate``.
"""

import base64
import codecs
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

from .errors import SandboxError

#: The signals ``kill`` can send, mapped to the API's enum values.
SIGNALS = {
    "SIGTERM": "SANDBOX_COMMAND_SIGNAL_SIGTERM",
    "SIGKILL": "SANDBOX_COMMAND_SIGNAL_SIGKILL",
}


@dataclass
class CommandInfo:
    """A command that is running in a sandbox."""

    pid: int
    cmd: str
    cwd: Optional[str] = None


@dataclass
class CommandResult:
    """The outcome of a command that exited. A non-zero ``exit_code`` is not an error."""

    pid: int
    exit_code: int
    stdout: str
    stderr: str
    #: A short status for the exit, such as ``exited``.
    status: Optional[str] = None
    #: Set when the process failed abnormally.
    error: Optional[str] = None


@dataclass
class CommandEvent:
    """One event of a command's output.

    ``type`` is ``started``, ``stdout``, ``stderr`` or ``exit``. ``pid`` is set
    on ``started``; ``data`` and ``text`` on ``stdout`` and ``stderr``;
    ``exit_code``, ``status`` and ``error`` on ``exit``.
    """

    type: str
    pid: Optional[int] = None
    data: bytes = b""
    text: str = ""
    exit_code: Optional[int] = None
    status: Optional[str] = None
    error: Optional[str] = None


def start_body(
    cmd: str,
    args: Optional[List[str]],
    cwd: Optional[str],
    env_vars: Optional[Mapping[str, str]],
    stdin: Optional[bool],
    timeout_seconds: Optional[int],
) -> Dict[str, Any]:
    """Validates start arguments and builds the request body."""
    if not cmd or not str(cmd).strip():
        raise SandboxError("commands.start: `cmd` is required")
    body: Dict[str, Any] = {"cmd": cmd}
    if args:
        body["args"] = list(args)
    if cwd:
        body["cwd"] = cwd
    if env_vars:
        body["env_vars"] = dict(env_vars)
    if stdin:
        body["stdin"] = True
    if timeout_seconds:
        # The API encodes this int64 as a string (protobuf JSON).
        body["timeout_seconds"] = str(int(timeout_seconds))
    return body


def stdin_body(data: Any, eof: bool) -> Dict[str, Any]:
    """Builds the stdin request body. ``data`` is str or bytes, or None for eof only."""
    body: Dict[str, Any] = {}
    if data:
        raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
        body["data"] = base64.b64encode(raw).decode("ascii")
    if eof:
        body["eof"] = True
    return body


def signal_value(signal: str) -> str:
    if signal not in SIGNALS:
        raise SandboxError(
            "commands: unsupported signal %s: expected SIGTERM or SIGKILL" % signal
        )
    return SIGNALS[signal]


def to_event(raw: Any) -> Optional[CommandEvent]:
    """Decodes one ``{"result": ...}`` or ``{"error": ...}`` envelope.

    Keepalives and unknown events return None. A stream error raises.
    """
    if not isinstance(raw, dict):
        return None
    if raw.get("error"):
        err = raw["error"]
        raise SandboxError(
            err.get("message") or "the command stream failed",
            status=int(err.get("http_code") or 0),
        )
    result = raw.get("result")
    if not isinstance(result, dict):
        return None
    if result.get("started"):
        return CommandEvent("started", pid=int(result["started"].get("pid", 0)))
    for kind in ("stdout", "stderr"):
        if result.get(kind):
            data = base64.b64decode(result[kind])
            return CommandEvent(kind, data=data, text=data.decode("utf-8", "replace"))
    if result.get("exit") is not None:
        exit_ = result["exit"]
        return CommandEvent(
            "exit",
            exit_code=int(exit_.get("exit_code") or 0),
            status=exit_.get("status") or None,
            error=exit_.get("error") or None,
        )
    return None


class JsonObjectReader:
    """Splits a stream of concatenated JSON objects (newline-delimited or not).

    ``push`` takes text and returns the parsed objects it completes, keeping a
    partial object for the next chunk. Braces inside strings do not count.
    """

    def __init__(self) -> None:
        self._buf = ""

    def push(self, text: str) -> List[Any]:
        self._buf += text
        out: List[Any] = []
        depth = 0
        in_string = False
        escaped = False
        start = -1
        consumed = 0
        for i, ch in enumerate(self._buf):
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}" and depth > 0:
                depth -= 1
                if depth == 0:
                    out.append(json.loads(self._buf[start : i + 1]))
                    consumed = i + 1
        self._buf = "" if depth == 0 else self._buf[start if start >= 0 else consumed :]
        return out


class TextAssembler:
    """Collects stdout and stderr as text without splitting a multi-byte character."""

    def __init__(self) -> None:
        self._out = codecs.getincrementaldecoder("utf-8")("replace")
        self._err = codecs.getincrementaldecoder("utf-8")("replace")
        self.stdout = ""
        self.stderr = ""

    def feed(self, event: CommandEvent) -> str:
        """Adds a stdout or stderr event and returns the text it completes."""
        dec = self._out if event.type == "stdout" else self._err
        text = dec.decode(event.data)
        if event.type == "stdout":
            self.stdout += text
        else:
            self.stderr += text
        return text

    def finish(self) -> None:
        self.stdout += self._out.decode(b"", final=True)
        self.stderr += self._err.decode(b"", final=True)
