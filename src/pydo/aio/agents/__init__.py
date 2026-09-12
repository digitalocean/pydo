# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async Hosted Agents API — hand-written; preserved across ``make generate``."""
from __future__ import annotations

from typing import Optional

from pydo.agents import _select_session_by_name, resolve_agents_base_url
from pydo.custom_extensions import _BaseURLProxy

from .custom_sessions import (
    AsyncHarnessEventStream,
    AsyncSessionsOperations,
    AsyncWorkspaceDownload,
)
from .session import AsyncAgentSession, AsyncRunStream


class AsyncAgentsResources:
    def __init__(self, parent_client, *, agents_endpoint: Optional[str] = None):
        self._proxy = _BaseURLProxy(
            parent_client._client,
            resolve_agents_base_url(agents_endpoint),
        )
        self.sessions = AsyncSessionsOperations(self._proxy)

    @property
    def base_url(self) -> str:
        return self._proxy._base_url

    async def start(self, manifest: "str | bytes") -> AsyncAgentSession:
        """Create a session from an ``agents.yaml`` manifest and return a handle.

        Use as ``async with await client.agents.start(manifest) as agent:`` to
        auto-destroy on exit.
        """
        resp = await self.sessions.create_from_manifest(manifest)
        get = getattr(resp, "get", None)
        info = get("session") if get else None
        session_id = (getattr(info or resp, "get", lambda *_: None))("session_id")
        return AsyncAgentSession(self.sessions, session_id, raw=resp)

    def attach(self, session_id: str) -> AsyncAgentSession:
        """Return an :class:`AsyncAgentSession` handle for an existing session."""
        return AsyncAgentSession(self.sessions, session_id)

    async def attach_by_name(self, name: str) -> AsyncAgentSession:
        """Resolve a session by ``name`` and return an :class:`AsyncAgentSession`.

        See :meth:`pydo.agents.AgentsResources.attach_by_name`.
        """
        resp = await self.sessions.list(name=name)
        session = _select_session_by_name(resp, name)
        session_id = (getattr(session, "get", lambda *_: None))("session_id")
        return AsyncAgentSession(self.sessions, session_id, raw=session)


__all__ = [
    "AsyncAgentsResources",
    "AsyncAgentSession",
    "AsyncRunStream",
    "AsyncSessionsOperations",
    "AsyncHarnessEventStream",
    "AsyncWorkspaceDownload",
]
