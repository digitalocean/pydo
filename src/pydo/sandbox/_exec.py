# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Types and helpers shared by the sync and async sandbox exec.

Hand-written; preserved across ``make generate``.
"""

import base64
import codecs
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from ._commands import JsonObjectReader, TextAssembler  # noqa: F401 (re-exported)
from .errors import SandboxError

#: A shell string, or an argv list.
Command = Union[str, Sequence[str]]

#: ``rows`` and ``cols`` must be in this range.
MIN_SIZE = 1
MAX_SIZE = 1000

STREAM_ENDED = "the exec stream ended before the process exited; its outcome is unknown"


@dataclass
class ExecResult:
    """The outcome of an exec that exited. A non-zero ``exit_code`` is not an error."""

    exit_code: int
    stdout: str
    stderr: str
    #: How long the process ran, in milliseconds.
    duration_ms: int = 0
    #: A short status for the exit, such as ``exited``.
    status: Optional[str] = None
    #: Set when the process failed abnormally.
    error: Optional[str] = None


@dataclass
class ExecEvent:
    """One event of an exec's output.

    ``type`` is ``started``, ``stdout``, ``stderr`` or ``exit``. ``exec_id`` is
    set on ``started``; ``data`` and ``text`` on ``stdout`` and ``stderr``;
    ``exit_code``, ``duration_ms``, ``status`` and ``error`` on ``exit``.
    """

    type: str
    exec_id: Optional[str] = None
    data: bytes = b""
    text: str = ""
    exit_code: Optional[int] = None
    duration_ms: Optional[int] = None
    status: Optional[str] = None
    error: Optional[str] = None


def _int(raw: Any) -> int:
    try:
        return int(raw) if raw not in (None, "") else 0
    except (TypeError, ValueError):
        return 0


def argv_for(command: Optional[Command], pty: bool = False) -> List[str]:
    """Builds argv: a string runs as ``bash -lc <command>``, a list is used as is.

    An empty argv is allowed only with a PTY (the guest's default shell).
    """
    if command is None or (not isinstance(command, str) and len(command) == 0):
        if pty:
            return []
        raise SandboxError("exec: `command` is required")
    if isinstance(command, str):
        if not command.strip():
            if pty:
                return []
            raise SandboxError("exec: `command` is required")
        return ["bash", "-lc", command]
    argv = list(command)
    if not all(isinstance(a, str) for a in argv):
        raise SandboxError("exec: every argv entry must be a string")
    if not argv[0]:
        raise SandboxError("exec: the first argv entry must not be empty")
    return argv


def _size(name: str, value: Any) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not MIN_SIZE <= value <= MAX_SIZE
    ):
        raise SandboxError(
            "exec: `%s` must be an integer from %d to %d" % (name, MIN_SIZE, MAX_SIZE)
        )
    return value


def to_bytes(data: Any) -> bytes:
    if isinstance(data, str):
        return data.encode("utf-8")
    if isinstance(data, (bytes, bytearray, memoryview)):
        return bytes(data)
    raise SandboxError("exec: stdin data must be str or bytes")


def pty_body(pty: Any) -> Optional[Dict[str, Any]]:
    """Validates the ``pty`` option: falsy for none, ``True`` or a mapping to turn it on."""
    if pty is None or pty is False:
        return None
    if pty is True:
        return {}
    if not isinstance(pty, Mapping):
        raise SandboxError("exec: `pty` must be True or a mapping of rows, cols, term")
    unknown = set(pty) - {"rows", "cols", "term"}
    if unknown:
        raise SandboxError("exec: unknown pty option %s" % ", ".join(sorted(unknown)))
    out: Dict[str, Any] = {}
    for key in ("rows", "cols"):
        if pty.get(key) is not None:
            out[key] = _size(key, pty[key])
    if pty.get("term"):
        out["term"] = str(pty["term"])
    return out


def exec_body(
    argv: List[str],
    cwd: Optional[str] = None,
    env_vars: Optional[Mapping[str, str]] = None,
    timeout_seconds: Optional[int] = None,
    keep_stdin_open: bool = False,
    pty: Any = None,
    stdin: Any = None,
) -> Dict[str, Any]:
    """Validates the options and builds the start request body."""
    body: Dict[str, Any] = {"argv": list(argv)}
    if cwd:
        body["workdir"] = cwd
    if env_vars:
        for key in env_vars:
            if not isinstance(key, str) or not key:
                raise SandboxError("exec: env var names must not be empty")
        body["env_vars"] = dict(env_vars)
    if timeout_seconds is not None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds < 0
        ):
            raise SandboxError("exec: `timeout_seconds` must be 0 or more")
        if timeout_seconds:
            # The API encodes this int64 as a string (protobuf JSON).
            body["timeout_seconds"] = str(int(timeout_seconds))
    if keep_stdin_open:
        body["keep_stdin_open"] = True
    pty_value = pty_body(pty)
    if pty_value is not None:
        body["pty"] = pty_value
    if stdin is not None:
        raw = to_bytes(stdin)
        if raw:
            body["stdin"] = base64.b64encode(raw).decode("ascii")
    return body


def stdin_body(data: Any, offset: int, eof: bool) -> Dict[str, Any]:
    """Builds the stdin request body. The int64 ``offset`` is sent as a string."""
    body: Dict[str, Any] = {"offset": str(offset)}
    if data:
        body["data"] = base64.b64encode(to_bytes(data)).decode("ascii")
    if eof:
        body["eof"] = True
    return body


def resize_body(rows: Any, cols: Any) -> Dict[str, Any]:
    return {"rows": _size("rows", rows), "cols": _size("cols", cols)}


def next_offset(response: Any, current: int, written: int) -> int:
    """The offset after a write: the server's, else ``current + written``."""
    if isinstance(response, dict) and response.get("offset") not in (None, ""):
        return _int(response["offset"])
    return current + written


def to_exec_event(raw: Any) -> Optional[ExecEvent]:
    """Decodes one ``{"result": ...}`` or ``{"error": ...}`` envelope.

    Keepalives and unknown events return None. A stream error raises.
    """
    if not isinstance(raw, dict):
        return None
    if raw.get("error"):
        err = raw["error"]
        if not isinstance(err, dict):
            err = {"message": str(err)}
        raise SandboxError(
            err.get("message") or "the exec stream failed",
            status=_int(err.get("http_code")),
        )
    result = raw.get("result")
    if not isinstance(result, dict):
        return None
    if result.get("started") is not None:
        return ExecEvent("started", exec_id=result["started"].get("exec_id") or None)
    for kind in ("stdout", "stderr"):
        if result.get(kind):
            data = base64.b64decode(result[kind])
            return ExecEvent(kind, data=data, text=data.decode("utf-8", "replace"))
    if result.get("exit") is not None:
        exit_ = result["exit"]
        return ExecEvent(
            "exit",
            # Protobuf JSON drops zero values: a missing exit_code is 0.
            exit_code=_int(exit_.get("exit_code")),
            duration_ms=_int(exit_.get("duration_ms")),
            status=exit_.get("status") or None,
            error=exit_.get("error") or None,
        )
    return None


def result_from(event: ExecEvent, text: TextAssembler) -> ExecResult:
    text.finish()
    return ExecResult(
        exit_code=event.exit_code or 0,
        stdout=text.stdout,
        stderr=text.stderr,
        duration_ms=event.duration_ms or 0,
        status=event.status,
        error=event.error,
    )
