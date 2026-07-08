# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Action Gateway constants, errors, and shared value types."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Meta-tool names exposed on the gateway's ``/mcp/meta`` endpoint.
META_SEARCH = "action.search"
META_INVOKE = "action.invoke"
META_CODE = "action.code"
META_TOOL_NAMES = frozenset({META_SEARCH, META_INVOKE, META_CODE})


class ToolResultStatus:
    """Status of a single tool invocation envelope."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ToolErrorClass:
    """Closed error taxonomy for tool invocation failures."""

    INVALID_ARGUMENT = "invalid_argument"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    UPSTREAM_ERROR = "upstream_error"
    OUTPUT_TOO_LARGE = "output_too_large"
    EXECUTION_FAILED = "execution_failed"
    UNAVAILABLE = "unavailable"


class RecoveryHint:
    """Machine-routable hint on how a caller should recover from a failure."""

    FIX_ARGS = "fix_args"
    RETRY = "retry"
    BACKOFF = "backoff"
    ESCALATE = "escalate"


class GatewayToolError(RuntimeError):
    """A tool invocation failed (gateway ``ToolResult`` error envelope).

    Raised when a single-tool operation (``invoke_one``, ``code.execute``,
    ``tools.call``) fails, or when the MCP result reports ``isError``.
    Batch ``invoke`` calls do NOT raise per-item failures; inspect the
    envelope instead.
    """

    def __init__(
        self,
        message: str,
        *,
        error_class: Optional[str] = None,
        retriable: Optional[bool] = None,
        recovery_hint: Optional[str] = None,
        invocation_id: Optional[str] = None,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_class = error_class
        self.retriable = retriable
        self.recovery_hint = recovery_hint
        self.invocation_id = invocation_id
        self.details = details

    @classmethod
    def from_error_payload(
        cls,
        error: Dict[str, Any],
        *,
        invocation_id: Optional[str] = None,
    ) -> "GatewayToolError":
        return cls(
            error.get("message") or "tool invocation failed",
            error_class=error.get("class"),
            retriable=error.get("retriable"),
            recovery_hint=error.get("recovery_hint"),
            invocation_id=invocation_id,
            details=error,
        )


class GatewayProtocolError(RuntimeError):
    """A JSON-RPC protocol-level error from the gateway MCP endpoint."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[int] = None,
        data: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data


class ToolCall:
    """A normalized tool call extracted from an inference response.

    ``arguments`` is always a decoded ``dict`` (providers JSON-decode the
    vendor's string encoding when needed).
    """

    __slots__ = ("call_id", "name", "arguments")

    def __init__(self, call_id: str, name: str, arguments: Dict[str, Any]):
        self.call_id = call_id
        self.name = name
        self.arguments = arguments

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"ToolCall(call_id={self.call_id!r}, name={self.name!r}, "
            f"arguments={self.arguments!r})"
        )


__all__: List[str] = [
    "META_SEARCH",
    "META_INVOKE",
    "META_CODE",
    "META_TOOL_NAMES",
    "ToolResultStatus",
    "ToolErrorClass",
    "RecoveryHint",
    "GatewayToolError",
    "GatewayProtocolError",
    "ToolCall",
]
