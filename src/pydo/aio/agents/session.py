# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async high-level agent interface (see :mod:`pydo.agents.session`)."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from pydo.agents.custom_models import ResolutionSource, SessionStatus
from pydo.agents.session import (
    AgentEvent,
    AgentEventType,
    HITLPolicy,
    RunResult,
    _decide_hitl,
)


class AsyncRunStream:
    """Async iterable of :class:`~pydo.agents.session.AgentEvent` for one run."""

    def __init__(
        self,
        *,
        raw_stream: Any,
        run_id: Optional[str],
        session: "AsyncAgentSession",
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

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        deadline = (
            (asyncio.get_event_loop().time() + self._timeout) if self._timeout else None
        )
        try:
            async for raw in self._raw:
                event = AgentEvent(raw)
                self.events.append(event)

                if event.type == AgentEventType.TOKEN:
                    self._chunks.append(event.text)
                elif event.type == AgentEventType.HITL_REQUESTED:
                    await self._auto_resolve(event)

                yield event

                if self._is_terminal(event):
                    break
                if deadline and asyncio.get_event_loop().time() > deadline:
                    self.status = "timeout"
                    break
        finally:
            await self.close()

    async def _auto_resolve(self, event: AgentEvent) -> None:
        outcome = _decide_hitl(self._hitl, event)
        if not outcome or not event.request_id:
            return
        try:
            await self._session.resolve_hitl(
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

    async def close(self) -> None:
        closer = getattr(self._raw, "close", None)
        if closer:
            try:
                await closer()
            except Exception:  # noqa: BLE001
                pass

    async def __aenter__(self) -> "AsyncRunStream":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


class AsyncAgentSession:
    """Async self-managing handle to one hosted-agent session."""

    def __init__(self, sessions: Any, session_id: str, *, raw: Any = None):
        self._sessions = sessions
        self.session_id = session_id
        self._raw = raw

    @property
    def sessions(self) -> Any:
        return self._sessions

    @property
    def info(self) -> Any:
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

    async def refresh(self) -> Any:
        self._raw = await self._sessions.get(self.session_id)
        return self.info

    async def wait_until_ready(
        self, *, timeout: float = 120.0, poll_interval: float = 2.0
    ) -> "AsyncAgentSession":
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        while True:
            info = await self.refresh()
            status = (getattr(info, "get", lambda *_: None))("status")
            if status == SessionStatus.READY:
                return self
            if status in (SessionStatus.FAILED, SessionStatus.DESTROYED):
                raise RuntimeError(f"session {self.session_id} is {status}")
            if loop.time() > deadline:
                raise TimeoutError(
                    f"session {self.session_id} not ready after {timeout}s"
                )
            await asyncio.sleep(poll_interval)

    async def run_streamed(
        self,
        prompt: str,
        *,
        hitl: HITLPolicy = "approve",
        timeout: Optional[float] = 300.0,
    ) -> AsyncRunStream:
        raw_stream = await self._sessions.stream(self.session_id)
        run = await self._sessions.send_input(self.session_id, text=prompt)
        run_id = (getattr(run, "get", lambda *_: None))("run_id")
        return AsyncRunStream(
            raw_stream=raw_stream,
            run_id=run_id,
            session=self,
            hitl=hitl,
            timeout=timeout,
        )

    async def run(
        self,
        prompt: str,
        *,
        hitl: HITLPolicy = "approve",
        timeout: Optional[float] = 300.0,
    ) -> RunResult:
        stream = await self.run_streamed(prompt, hitl=hitl, timeout=timeout)
        async for _ in stream:
            pass
        return stream.result

    # --- thin passthroughs (session id bound) ---------------------------
    async def send_input(self, text: str) -> Any:
        return await self._sessions.send_input(self.session_id, text=text)

    async def pause(self) -> Any:
        return await self._sessions.pause(self.session_id)

    async def resume(self) -> Any:
        return await self._sessions.resume(self.session_id)

    async def stream(self, **kwargs: Any) -> Any:
        return await self._sessions.stream(self.session_id, **kwargs)

    async def resolve_hitl(
        self,
        request_id: str,
        *,
        outcome: str,
        reason: Optional[str] = None,
        source: Optional[str] = None,
    ) -> None:
        await self._sessions.resolve_hitl(
            self.session_id,
            request_id,
            outcome=outcome,
            reason=reason,
            source=source,
        )

    async def upload_file(
        self,
        *,
        path: str,
        data: Any,
        is_archive: bool = False,
        content_sha256: Optional[str] = None,
    ) -> Any:
        """Upload bytes/a tar into the session workspace."""
        return await self._sessions.workspace_upload(
            self.session_id,
            path=path,
            data=data,
            is_archive=is_archive,
            content_sha256=content_sha256,
        )

    async def download_file(
        self,
        *,
        path: str,
        as_archive: bool = False,
        require_checksum: bool = False,
    ) -> Any:
        """Download a workspace file/tar with integrity verification."""
        return await self._sessions.workspace_download(
            self.session_id,
            path=path,
            as_archive=as_archive,
            require_checksum=require_checksum,
        )

    async def destroy(self) -> None:
        await self._sessions.destroy(self.session_id)

    async def __aenter__(self) -> "AsyncAgentSession":
        return self

    async def __aexit__(self, *args: Any) -> None:
        try:
            await self.destroy()
        except Exception:  # noqa: BLE001 - teardown best-effort
            pass

    def __repr__(self) -> str:
        return f"AsyncAgentSession(session_id={self.session_id!r})"


__all__ = ["AsyncAgentSession", "AsyncRunStream"]
