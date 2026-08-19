# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Hosted Agents (Harness) API — hand-written; preserved across ``make generate``."""
from __future__ import annotations

import os
from typing import Optional

from pydo.custom_extensions import _BaseURLProxy

from .custom_models import (
    AgentKind,
    HITLActionKind,
    HITLOutcome,
    OAuthProvider,
    ProviderAuthState,
    ResolutionSource,
    RunFailureCode,
    RunState,
    SessionStatus,
    SignatureScheme,
    TriggerExecutionStatus,
    TriggerKind,
    TriggerOutputMode,
    TriggerSessionMode,
    TriggerStatus,
    WebhookProviderKey,
)
from .custom_sessions import (
    HarnessEventStream,
    HarnessStreamError,
    HistoryPage,
    SessionsOperations,
    WorkspaceDownload,
    WorkspaceTransferError,
)
from .custom_triggers import TriggersOperations
from .custom_openai_sandbox import (
    OPENAI_CODEX_ADAPTERS,
    OpenAIAgentsError,
    is_openai_codex_manifest,
    is_openai_codex_session,
    prepare_openai_codex_manifest,
    resolve_placeholders,
)
from .session import (
    AgentEvent,
    AgentEventType,
    AgentSession,
    HITLPolicy,
    RunResult,
    RunStream,
)

DEFAULT_AGENTS_BASE_URL = "https://api.digitalocean.com"
_ENV_VAR = "PYDO_AGENTS_ENDPOINT"


def _looks_like_openai_codex_manifest(manifest: "str | bytes") -> bool:
    """Cheap text heuristic used before full YAML parse / OpenAI orchestration."""
    text = (
        manifest
        if isinstance(manifest, str)
        else bytes(manifest).decode("utf-8", errors="replace")
    )
    if "openai-agent-codex" in text or "codex-agentapi" in text:
        return True
    # ``spec.openai:`` block (design §3)
    return "\n  openai:" in text or text.lstrip().startswith("openai:")


def resolve_agents_base_url(explicit: Optional[str] = None) -> str:
    url = explicit or os.environ.get(_ENV_VAR) or DEFAULT_AGENTS_BASE_URL
    url = url.rstrip("/")
    if "://" not in url:
        url = f"https://{url}"
    return url


def _select_session_by_name(list_response, name: str):
    """Pick the most recently created session from a name-filtered list.

    Raises :class:`LookupError` when the response contains no sessions.
    """
    get = getattr(list_response, "get", None)
    sessions = (get("sessions") if get else None) or []
    if not sessions:
        raise LookupError(f"no session found with name {name!r}")
    return max(
        sessions,
        key=lambda s: (getattr(s, "get", lambda *_: "")("created_at") or ""),
    )


class AgentsResources:
    def __init__(self, parent_client, *, agents_endpoint: Optional[str] = None):
        self._proxy = _BaseURLProxy(
            parent_client._client,
            resolve_agents_base_url(agents_endpoint),
        )
        self.sessions = SessionsOperations(self._proxy)
        self.triggers = TriggersOperations(self._proxy)

    @property
    def base_url(self) -> str:
        return self._proxy._base_url

    def start(
        self,
        manifest: "str | bytes",
        *,
        openai_api_key: Optional[str] = None,
        openai_session_id: Optional[str] = None,
        openai_environment_id: Optional[str] = None,
        openai_base_url: Optional[str] = None,
    ) -> AgentSession:
        """Create a session from an ``agents.yaml`` manifest and return a handle.

        For managed-loop adapters this uploads the manifest verbatim.

        For OpenAI sandbox-provider manifests (``spec.openai`` / adapters in
        :data:`~pydo.agents.custom_openai_sandbox.OPENAI_CODEX_ADAPTERS`) this mirrors
        doctl ``agents start``: create the OpenAI session (unless
        ``openai_session_id`` + ``openai_environment_id`` are already known),
        resolve ``${ENV_ID}`` / ``${OPENAI_API_KEY}`` into ``spec.env``, then
        create the DO session with ``openai_session_id`` as a query param.

        Use as a context manager to auto-destroy on exit::

            with client.agents.start(manifest) as agent:
                print(agent.run("hello").final_output)
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
            )

        resp = self.sessions.create_from_manifest(
            resolved,
            openai_session_id=oai_session_id,
        )
        get = getattr(resp, "get", None)
        info = get("session") if get else None
        session_id = (getattr(info or resp, "get", lambda *_: None))("session_id")
        return AgentSession(
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
    ) -> AgentSession:
        """Return an :class:`AgentSession` handle for an existing session.

        For ``AGENT_KIND_OPENAI_CODEX`` sessions, pass ``openai_api_key`` (or
        set ``OPENAI_API_KEY``) so :meth:`~pydo.agents.session.AgentSession.run`
        bridges to OpenAI instead of DO's event stream.
        """
        return AgentSession(
            self.sessions,
            session_id,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
        )

    def attach_by_name(
        self,
        name: str,
        *,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
    ) -> AgentSession:
        """Resolve a session by ``name`` and return an :class:`AgentSession`.

        Looks up ``GET /v2/agents/sessions?name=<name>``. If several sessions
        share the name (e.g. reused over time), the most recently created one
        is chosen. Raises :class:`LookupError` when there is no match.
        """
        resp = self.sessions.list(name=name)
        session = _select_session_by_name(resp, name)
        session_id = (getattr(session, "get", lambda *_: None))("session_id")
        return AgentSession(
            self.sessions,
            session_id,
            raw=session,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
        )


__all__ = [
    "AgentsResources",
    "AgentSession",
    "AgentEvent",
    "AgentEventType",
    "RunResult",
    "RunStream",
    "HITLPolicy",
    "SessionsOperations",
    "TriggersOperations",
    "HarnessEventStream",
    "HarnessStreamError",
    "HistoryPage",
    "WorkspaceDownload",
    "WorkspaceTransferError",
    "DEFAULT_AGENTS_BASE_URL",
    "resolve_agents_base_url",
    "OPENAI_CODEX_ADAPTERS",
    "OpenAIAgentsError",
    "is_openai_codex_manifest",
    "is_openai_codex_session",
    "prepare_openai_codex_manifest",
    "resolve_placeholders",
    "AgentKind",
    "SessionStatus",
    "RunState",
    "RunFailureCode",
    "HITLOutcome",
    "HITLActionKind",
    "ResolutionSource",
    "OAuthProvider",
    "ProviderAuthState",
    "TriggerKind",
    "TriggerStatus",
    "TriggerSessionMode",
    "TriggerOutputMode",
    "WebhookProviderKey",
    "TriggerExecutionStatus",
    "SignatureScheme",
]
