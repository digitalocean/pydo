# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async Hosted Agents API — hand-written; preserved across ``make generate``."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from pydo.agents import (
    _looks_like_openai_codex_manifest,
    _select_session_by_name,
    emit_session_create_warnings,
    prepare_openai_codex_manifest,
    resolve_agents_base_url,
    resolve_placeholders,
    session_create_warnings,
)
from pydo.custom_extensions import _BaseURLProxy

from .custom_sessions import (
    AsyncHarnessEventStream,
    AsyncSessionsOperations,
    AsyncWorkspaceDownload,
)
from .custom_configs import AsyncConfigsOperations
from .custom_templates import AsyncTemplatesOperations
from .custom_triggers import AsyncTriggersOperations
from .session import AsyncAgentSession, AsyncRunStream


class AsyncAgentsResources:
    def __init__(self, parent_client, *, agents_endpoint: Optional[str] = None):
        self._proxy = _BaseURLProxy(
            parent_client._client,
            resolve_agents_base_url(agents_endpoint),
        )
        self.sessions = AsyncSessionsOperations(self._proxy)
        self.configs = AsyncConfigsOperations(self._proxy)
        self.templates = AsyncTemplatesOperations(self._proxy)
        self.triggers = AsyncTriggersOperations(self._proxy)

    @property
    def base_url(self) -> str:
        return self._proxy._base_url

    async def start(
        self,
        manifest: "str | bytes",
        *,
        openai_api_key: Optional[str] = None,
        openai_session_id: Optional[str] = None,
        openai_environment_id: Optional[str] = None,
        openai_remote_url: Optional[str] = None,
        openai_base_url: Optional[str] = None,
    ) -> AsyncAgentSession:
        """Create a session from an ``agents.yaml`` manifest and return a handle.

        See :meth:`pydo.agents.AgentsResources.start`.
        """
        resolved: "str | bytes" = manifest
        oai_session_id = openai_session_id

        if openai_session_id or _looks_like_openai_codex_manifest(manifest):
            resolved, oai_session_id, _env_id = prepare_openai_codex_manifest(
                manifest,
                openai_api_key=openai_api_key,
                openai_base_url=openai_base_url,
                openai_session_id=openai_session_id,
                openai_environment_id=openai_environment_id,
                openai_remote_url=openai_remote_url,
            )

        resp = await self.sessions.create_from_manifest(
            resolved,
            openai_session_id=oai_session_id,
        )
        emit_session_create_warnings(session_create_warnings(resp), stacklevel=2)
        get = getattr(resp, "get", None)
        info = get("session") if get else None
        session_id = (getattr(info or resp, "get", lambda *_: None))("session_id")
        return AsyncAgentSession(
            self.sessions,
            session_id,
            raw=resp,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
        )

    def attach(
        self,
        session_id: str,
        *,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
    ) -> AsyncAgentSession:
        """Return an :class:`AsyncAgentSession` handle for an existing session."""
        return AsyncAgentSession(
            self.sessions,
            session_id,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
        )

    async def attach_by_name(
        self,
        name: str,
        *,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
    ) -> AsyncAgentSession:
        """Resolve a session by ``name`` and return an :class:`AsyncAgentSession`.

        See :meth:`pydo.agents.AgentsResources.attach_by_name`.
        """
        resp = await self.sessions.list(name=name)
        session = _select_session_by_name(resp, name)
        session_id = (getattr(session, "get", lambda *_: None))("session_id")
        return AsyncAgentSession(
            self.sessions,
            session_id,
            raw=session,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
        )

    async def create_session(
        self,
        *,
        params: Optional[Mapping[str, Any]] = None,
        body: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Boot a sandbox for an existing OpenAI session (docs-compatible API).

        See :meth:`pydo.agents.AgentsResources.create_session`.
        """
        if body is None or "manifest" not in body:
            raise ValueError("body.manifest is required")
        manifest = body["manifest"]
        variables = body.get("variables") or {}
        if variables:
            if isinstance(manifest, (bytes, bytearray)):
                text = bytes(manifest).decode("utf-8")
            else:
                text = str(manifest)
            replacements = {str(k): str(v) for k, v in dict(variables).items()}
            manifest = resolve_placeholders(text, replacements)

        openai_session_id = None
        if params:
            openai_session_id = params.get("openai_session_id")

        resp = await self.sessions.create_from_manifest(
            manifest,
            openai_session_id=openai_session_id,
            timeout=timeout,
        )
        emit_session_create_warnings(session_create_warnings(resp), stacklevel=2)
        return resp

    async def destroy_session(self, *, session_id: str) -> None:
        """Release a sandbox session (docs-compatible API)."""
        if not session_id:
            raise ValueError("session_id is required")
        await self.sessions.destroy(session_id)


__all__ = [
    "AsyncAgentsResources",
    "AsyncAgentSession",
    "AsyncRunStream",
    "AsyncSessionsOperations",
    "AsyncConfigsOperations",
    "AsyncTemplatesOperations",
    "AsyncTriggersOperations",
    "AsyncHarnessEventStream",
    "AsyncWorkspaceDownload",
]
