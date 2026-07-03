# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Hosted Agents API enum string constants."""
from __future__ import annotations


class AgentKind:
    """Discriminator for what runs inside a session's sandbox."""

    UNSPECIFIED = "AGENT_KIND_UNSPECIFIED"
    CLAUDE_CODE = "AGENT_KIND_CLAUDE_CODE"
    OPENCODE = "AGENT_KIND_OPENCODE"
    CODEX_CLI = "AGENT_KIND_CODEX_CLI"
    CURSOR_CLI = "AGENT_KIND_CURSOR_CLI"
    NONE = "AGENT_KIND_NONE"
    CUSTOM = "AGENT_KIND_CUSTOM"


class SessionStatus:
    """Lifecycle states for a session."""

    UNSPECIFIED = "SESSION_STATUS_UNSPECIFIED"
    PROVISIONING = "SESSION_STATUS_PROVISIONING"
    READY = "SESSION_STATUS_READY"
    DETACHED = "SESSION_STATUS_DETACHED"
    PAUSED = "SESSION_STATUS_PAUSED"
    DESTROYING = "SESSION_STATUS_DESTROYING"
    DESTROYED = "SESSION_STATUS_DESTROYED"
    FAILED = "SESSION_STATUS_FAILED"


class RunState:
    """Finite-state machine for an individual agent run inside a session."""

    UNSPECIFIED = "RUN_STATE_UNSPECIFIED"
    QUEUED = "RUN_STATE_QUEUED"
    RUNNING = "RUN_STATE_RUNNING"
    AWAITING_HITL = "RUN_STATE_AWAITING_HITL"
    PAUSED = "RUN_STATE_PAUSED"
    COMPLETED = "RUN_STATE_COMPLETED"
    FAILED = "RUN_STATE_FAILED"


class RunFailureCode:
    """Canonical reasons a run can fail. Closed enum; routable by clients."""

    UNSPECIFIED = "RUN_FAILURE_CODE_UNSPECIFIED"
    MODEL_ERROR = "RUN_FAILURE_CODE_MODEL_ERROR"
    MODEL_TIMEOUT = "RUN_FAILURE_CODE_MODEL_TIMEOUT"
    TOOL_ERROR = "RUN_FAILURE_CODE_TOOL_ERROR"
    SANDBOX_LOST = "RUN_FAILURE_CODE_SANDBOX_LOST"
    HITL_REJECTED = "RUN_FAILURE_CODE_HITL_REJECTED"
    BUDGET_EXCEEDED = "RUN_FAILURE_CODE_BUDGET_EXCEEDED"
    INTERNAL = "RUN_FAILURE_CODE_INTERNAL"


class HITLOutcome:
    """User decision on a pending HITL request."""

    UNSPECIFIED = "HITL_OUTCOME_UNSPECIFIED"
    APPROVE = "HITL_OUTCOME_APPROVE"
    REJECT = "HITL_OUTCOME_REJECT"
    DEFER = "HITL_OUTCOME_DEFER"


class HITLActionKind:
    """Classifies the action the agent is asking permission for."""

    UNSPECIFIED = "HITL_ACTION_KIND_UNSPECIFIED"
    BASH = "HITL_ACTION_BASH"
    FILE_WRITE_OUTSIDE_WORKSPACE = "HITL_ACTION_FILE_WRITE_OUTSIDE_WORKSPACE"
    GITHUB_COMMIT_PUSH = "HITL_ACTION_GITHUB_COMMIT_PUSH"
    GITHUB_CREATE_PR = "HITL_ACTION_GITHUB_CREATE_PR"
    GITHUB_BRANCH_DELETE = "HITL_ACTION_GITHUB_BRANCH_DELETE"
    GITHUB_FORCE_PUSH = "HITL_ACTION_GITHUB_FORCE_PUSH"


class ResolutionSource:
    """How a HITL resolution was triggered. Captured for audit / UX analytics."""

    UNSPECIFIED = "RESOLUTION_SOURCE_UNSPECIFIED"
    INLINE_KEYSTROKE = "RESOLUTION_SOURCE_INLINE_KEYSTROKE"
    OUT_OF_BAND = "RESOLUTION_SOURCE_OUT_OF_BAND"


class OAuthProvider:
    """External identity provider a session is linking to."""

    UNSPECIFIED = "OAUTH_PROVIDER_UNSPECIFIED"
    GITHUB = "OAUTH_PROVIDER_GITHUB"


class OAuthFlowKind:
    """Interaction model the client should drive the developer through."""

    UNSPECIFIED = "OAUTH_FLOW_KIND_UNSPECIFIED"
    WEB_CALLBACK = "OAUTH_FLOW_KIND_WEB_CALLBACK"
    DEVICE = "OAUTH_FLOW_KIND_DEVICE"


class ProviderAuthState:
    """OAuth state for a single provider in ``Session.provider_auth``."""

    UNSPECIFIED = "PROVIDER_AUTH_STATE_UNSPECIFIED"
    NONE = "PROVIDER_AUTH_STATE_NONE"
    PENDING = "PROVIDER_AUTH_STATE_PENDING"
    AUTHORIZED = "PROVIDER_AUTH_STATE_AUTHORIZED"
    EXPIRED = "PROVIDER_AUTH_STATE_EXPIRED"


__all__ = [
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
