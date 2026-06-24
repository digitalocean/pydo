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
    OAuthFlowKind,
    OAuthProvider,
    ProviderAuthState,
    ResolutionSource,
    RunFailureCode,
    RunState,
    SessionStatus,
)
from .custom_sessions import HarnessEventStream, HarnessStreamError, SessionsOperations
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


def resolve_agents_base_url(explicit: Optional[str] = None) -> str:
    url = explicit or os.environ.get(_ENV_VAR) or DEFAULT_AGENTS_BASE_URL
    url = url.rstrip("/")
    if "://" not in url:
        url = f"https://{url}"
    return url


class AgentsResources:
    def __init__(self, parent_client, *, agents_endpoint: Optional[str] = None):
        self._proxy = _BaseURLProxy(
            parent_client._client,
            resolve_agents_base_url(agents_endpoint),
        )
        self.sessions = SessionsOperations(self._proxy)

    @property
    def base_url(self) -> str:
        return self._proxy._base_url

    def start(self, manifest: "str | bytes") -> AgentSession:
        """Create a session from an ``agents.yaml`` manifest and return a handle.

        Use as a context manager to auto-destroy on exit::

            with client.agents.start(manifest) as agent:
                print(agent.run("hello").final_output)
        """
        resp = self.sessions.create_from_manifest(manifest)
        get = getattr(resp, "get", None)
        info = get("session") if get else None
        session_id = (getattr(info or resp, "get", lambda *_: None))("session_id")
        return AgentSession(self.sessions, session_id, raw=resp)

    def attach(self, session_id: str) -> AgentSession:
        """Return an :class:`AgentSession` handle for an existing session."""
        return AgentSession(self.sessions, session_id)


__all__ = [
    "AgentsResources",
    "AgentSession",
    "AgentEvent",
    "AgentEventType",
    "RunResult",
    "RunStream",
    "HITLPolicy",
    "SessionsOperations",
    "HarnessEventStream",
    "HarnessStreamError",
    "DEFAULT_AGENTS_BASE_URL",
    "resolve_agents_base_url",
    "AgentKind",
    "SessionStatus",
    "RunState",
    "RunFailureCode",
    "HITLOutcome",
    "HITLActionKind",
    "ResolutionSource",
    "OAuthProvider",
    "OAuthFlowKind",
    "ProviderAuthState",
]
