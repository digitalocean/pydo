# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""High-level, self-contained agent interface over the Hosted Agents session API.

The low-level :class:`~pydo.agents.custom_sessions.SessionsOperations` mirrors the
REST endpoints one-to-one, which means consuming a run requires hand-wiring the
SSE feed: spawn a reader, dispatch on raw ``run.*`` event strings, accumulate
token deltas, resolve HITL prompts, and coordinate completion.

This module wraps that into an ergonomic surface inspired by
``openai-agents-python``::

    with client.agents.start(manifest) as agent:        # create + auto-destroy
        result = agent.run("Summarize the repo")        # blocking
        print(result.final_output)

        for event in agent.run_streamed("Now add tests"):  # streamed, typed
            if event.type == AgentEventType.TOKEN:
                print(event.text, end="")

No threads, no raw event-string matching, no manual teardown.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Union

from .custom_models import HITLOutcome, ResolutionSource, SessionStatus

# Normalized event type -> raw SPI ``type`` it maps from.
_RAW_TO_TYPE = {
    "run.started": "run_started",
    "run.token_delta": "token",
    "run.tool_call_started": "tool_call",
    "run.tool_call_completed": "tool_result",
    "run.human_input_requested": "hitl_requested",
    "run.human_input_received": "hitl_resolved",
    "run.completed": "completed",
    "run.failed": "failed",
}

_HITL_OUTCOMES = {
    "approve": HITLOutcome.APPROVE,
    "reject": HITLOutcome.REJECT,
    "defer": HITLOutcome.DEFER,
}

# A HITL policy is either a fixed decision ("approve"/"reject"/"defer"), an
# explicit HITLOutcome constant, a callable mapping an event -> decision, or
# None to leave prompts unresolved for the caller to handle.
HITLPolicy = Union[str, Callable[["AgentEvent"], Optional[str]], None]


class AgentEventType:
    """Normalized, friendly event kinds yielded by a run stream."""

    RUN_STARTED = "run_started"
    TOKEN = "token"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    HITL_REQUESTED = "hitl_requested"
    HITL_RESOLVED = "hitl_resolved"
    COMPLETED = "completed"
    FAILED = "failed"
    OTHER = "other"


class AgentEvent:
    """A normalized view over a raw harness SSE event.

    Exposes a stable :attr:`type` (see :class:`AgentEventType`) plus typed
    accessors, while keeping the underlying event available as :attr:`raw`.
    """

    def __init__(self, raw: Any):
        self.raw = raw
        get = getattr(raw, "get", None)
        self.raw_type: Optional[str] = get("type") if get else None
        self.type = _RAW_TO_TYPE.get(self.raw_type or "", AgentEventType.OTHER)
        data = get("data") if get else None
        self.data = data if data is not None else {}
        self.run_id: str = (get("run_id") if get else None) or ""

    def _d(self, key: str, default: Any = None) -> Any:
        get = getattr(self.data, "get", None)
        return get(key, default) if get else default

    @property
    def text(self) -> str:
        """Token text for ``TOKEN`` events ("" otherwise)."""
        return self._d("text", "") or ""

    @property
    def tool_name(self) -> Optional[str]:
        """Tool name for ``TOOL_CALL`` events."""
        return self._d("name")

    @property
    def request_id(self) -> Optional[str]:
        """HITL request id for ``HITL_REQUESTED`` / ``HITL_RESOLVED`` events."""
        return self._d("hitl_id") or self._d("request_id")

    @property
    def usage(self) -> Dict[str, Any]:
        """Token/cost totals for ``COMPLETED`` events."""
        return {
            "tokens_in": self._d("total_tokens_in"),
            "tokens_out": self._d("total_tokens_out"),
            "cost_micros": self._d("run_cost_micros"),
        }

    @property
    def error(self) -> Optional[Dict[str, Any]]:
        """Failure ``{code, message}`` for ``FAILED`` events."""
        if self.type != AgentEventType.FAILED:
            return None
        return {"code": self._d("code"), "message": self._d("message")}

    def __repr__(self) -> str:
        return f"AgentEvent(type={self.type!r}, run_id={self.run_id!r})"


class RunResult:
    """The outcome of a single run: assembled output, usage, and raw events."""

    def __init__(
        self,
        *,
        run_id: Optional[str],
        final_output: str,
        events: List[AgentEvent],
        usage: Dict[str, Any],
        status: str,
        error: Optional[Dict[str, Any]] = None,
    ):
        self.run_id = run_id
        self.final_output = final_output
        self.events = events
        self.usage = usage
        self.status = status  # "completed" | "failed" | "timeout"
        self.error = error

    @property
    def ok(self) -> bool:
        return self.status == "completed"

    def __str__(self) -> str:
        return self.final_output

    def __repr__(self) -> str:
        return (
            f"RunResult(status={self.status!r}, run_id={self.run_id!r}, "
            f"chars={len(self.final_output)})"
        )


def _decide_hitl(policy: HITLPolicy, event: AgentEvent) -> Optional[str]:
    """Resolve a HITL policy to a concrete outcome constant (or None)."""
    decision: Any = policy(event) if callable(policy) else policy
    if not decision:
        return None
    if isinstance(decision, str):
        return _HITL_OUTCOMES.get(decision.lower(), decision)
    return decision


class RunStream:
    """Iterable of :class:`AgentEvent` for one run.

    Iterating yields normalized events, auto-resolves HITL prompts per the
    configured policy, and accumulates the assembled output. After iteration,
    :attr:`final_output`, :attr:`usage`, :attr:`status`, and :attr:`result`
    are populated.
    """

    def __init__(
        self,
        *,
        raw_stream: Any,
        run_id: Optional[str],
        session: "AgentSession",
        hitl: HITLPolicy = "approve",
        timeout: Optional[float] = None,
    ):
        self._raw = raw_stream
        self.run_id = run_id
        self._session = session
        self._hitl = hitl
        self._timeout = timeout
        self._chunks: List[str] = []
        self.events: List[AgentEvent] = []
        self.usage: Dict[str, Any] = {}
        self.status = "running"
        self.error: Optional[Dict[str, Any]] = None

    def __iter__(self):
        deadline = time.monotonic() + self._timeout if self._timeout else None
        try:
            for raw in self._raw:
                event = AgentEvent(raw)
                self.events.append(event)

                if event.type == AgentEventType.TOKEN:
                    self._chunks.append(event.text)
                elif event.type == AgentEventType.HITL_REQUESTED:
                    self._auto_resolve(event)

                yield event

                if self._is_terminal(event):
                    break
                if deadline and time.monotonic() > deadline:
                    self.status = "timeout"
                    break
        finally:
            self.close()

    def _auto_resolve(self, event: AgentEvent) -> None:
        outcome = _decide_hitl(self._hitl, event)
        if not outcome or not event.request_id:
            return
        try:
            self._session.resolve_hitl(
                event.request_id,
                outcome=outcome,
                source=ResolutionSource.OUT_OF_BAND,
            )
        except Exception:  # noqa: BLE001 - best-effort; surfaced via the feed
            pass

    def _is_terminal(self, event: AgentEvent) -> bool:
        if self.run_id and event.run_id and event.run_id != self.run_id:
            return False
        if event.type == AgentEventType.COMPLETED:
            self.usage = event.usage
            self.status = "completed"
            return True
        if event.type == AgentEventType.FAILED:
            self.error = event.error
            self.status = "failed"
            return True
        return False

    @property
    def final_output(self) -> str:
        return "".join(self._chunks).strip()

    @property
    def result(self) -> RunResult:
        return RunResult(
            run_id=self.run_id,
            final_output=self.final_output,
            events=self.events,
            usage=self.usage,
            status=self.status,
            error=self.error,
        )

    def close(self) -> None:
        closer = getattr(self._raw, "close", None)
        if closer:
            try:
                closer()
            except Exception:  # noqa: BLE001
                pass

    def __enter__(self) -> "RunStream":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AgentSession:
    """A self-managing handle to one hosted-agent session.

    Wraps :class:`~pydo.agents.custom_sessions.SessionsOperations`, binding the
    ``session_id`` so callers never re-pass it, and adds :meth:`run` /
    :meth:`run_streamed`. Use as a context manager to auto-destroy on exit.
    """

    def __init__(self, sessions: Any, session_id: str, *, raw: Any = None):
        self._sessions = sessions
        self.session_id = session_id
        self._raw = raw

    @property
    def sessions(self) -> Any:
        """The underlying low-level operations object."""
        return self._sessions

    @property
    def info(self) -> Any:
        """The most recent session object (``{...}``), if known."""
        raw = self._raw
        if raw is None:
            return None
        get = getattr(raw, "get", None)
        inner = get("session") if get else None
        return inner if inner is not None else raw

    @property
    def status(self) -> Optional[str]:
        info = self.info
        get = getattr(info, "get", None)
        return get("status") if get else None

    def refresh(self) -> Any:
        """Fetch and cache the latest session state."""
        self._raw = self._sessions.get(self.session_id)
        return self.info

    def wait_until_ready(
        self, *, timeout: float = 120.0, poll_interval: float = 2.0
    ) -> "AgentSession":
        """Block until the session reports ``READY`` (or raise)."""
        deadline = time.monotonic() + timeout
        while True:
            status = (getattr(self.refresh(), "get", lambda *_: None))("status")
            if status == SessionStatus.READY:
                return self
            if status in (SessionStatus.FAILED, SessionStatus.DESTROYED):
                raise RuntimeError(f"session {self.session_id} is {status}")
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"session {self.session_id} not ready after {timeout}s"
                )
            time.sleep(poll_interval)

    def run_streamed(
        self,
        prompt: str,
        *,
        hitl: HITLPolicy = "approve",
        timeout: Optional[float] = 300.0,
    ) -> RunStream:
        """Send ``prompt`` and return a :class:`RunStream` of typed events.

        The SSE subscription is opened *before* the input is submitted, so no
        early events are missed — no caller-managed thread required.
        """
        raw_stream = self._sessions.stream(self.session_id)
        run = self._sessions.send_input(self.session_id, text=prompt)
        run_id = (getattr(run, "get", lambda *_: None))("run_id")
        return RunStream(
            raw_stream=raw_stream,
            run_id=run_id,
            session=self,
            hitl=hitl,
            timeout=timeout,
        )

    def run(
        self,
        prompt: str,
        *,
        hitl: HITLPolicy = "approve",
        timeout: Optional[float] = 300.0,
    ) -> RunResult:
        """Send ``prompt`` and block until the run finishes, returning a result."""
        stream = self.run_streamed(prompt, hitl=hitl, timeout=timeout)
        for _ in stream:
            pass
        return stream.result

    # --- thin passthroughs (session id bound) ---------------------------
    def send_input(self, text: str) -> Any:
        return self._sessions.send_input(self.session_id, text=text)

    def stream(self, **kwargs: Any) -> Any:
        return self._sessions.stream(self.session_id, **kwargs)

    def resolve_hitl(
        self,
        request_id: str,
        *,
        outcome: str,
        reason: Optional[str] = None,
        source: Optional[str] = None,
    ) -> None:
        self._sessions.resolve_hitl(
            self.session_id,
            request_id,
            outcome=outcome,
            reason=reason,
            source=source,
        )

    def upload_file(
        self,
        *,
        path: str,
        data: Any,
        is_archive: bool = False,
        content_sha256: Optional[str] = None,
    ) -> Any:
        """Upload bytes/a tar into the session workspace (see
        :meth:`SessionsOperations.workspace_upload`)."""
        return self._sessions.workspace_upload(
            self.session_id,
            path=path,
            data=data,
            is_archive=is_archive,
            content_sha256=content_sha256,
        )

    def download_file(
        self,
        *,
        path: str,
        as_archive: bool = False,
        require_checksum: bool = False,
    ) -> Any:
        """Download a workspace file/tar with integrity verification (see
        :meth:`SessionsOperations.workspace_download`)."""
        return self._sessions.workspace_download(
            self.session_id,
            path=path,
            as_archive=as_archive,
            require_checksum=require_checksum,
        )

    def destroy(self) -> None:
        self._sessions.destroy(self.session_id)

    def __enter__(self) -> "AgentSession":
        return self

    def __exit__(self, *args: Any) -> None:
        try:
            self.destroy()
        except Exception:  # noqa: BLE001 - teardown best-effort
            pass

    def __repr__(self) -> str:
        return f"AgentSession(session_id={self.session_id!r})"


__all__ = [
    "AgentEvent",
    "AgentEventType",
    "AgentSession",
    "RunResult",
    "RunStream",
    "HITLPolicy",
]
