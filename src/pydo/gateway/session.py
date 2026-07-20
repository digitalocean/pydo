# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
# pylint: disable=duplicate-code
"""Action Gateway sessions — create on the DO API, execute on the gateway."""

from __future__ import annotations

import json as _json
import uuid
from typing import Any, Dict, List, Optional, Sequence

from azure.core.rest import HttpRequest

from pydo.custom_extensions import _BaseURLProxy

from .custom_models import GatewayProtocolError
from .custom_operations import CodeOperations, ToolsOperations
from .providers import BaseProvider, default_provider, execute_tool_calls
from .transport import (
    RESTTransport,
    _parse_json_body,
    _raise_gateway_http_error,
    resolve_gateway_base_url,
    session_mcp_url,
)

_SESSIONS_PATH = "/v2/sessions"
_DEFAULT_POLICY: Dict[str, Any] = {"defaultAction": "allow", "rules": []}


def _pick(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def normalize_permissions(permissions: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize SDK permissions into the wire policy object.

    Accepts snake_case ``default_action`` or wire ``defaultAction``. When
    omitted, returns ``{"defaultAction": "allow", "rules": []}``.
    """
    if permissions is None:
        return dict(_DEFAULT_POLICY)

    default_action = (
        permissions.get("default_action")
        if "default_action" in permissions
        else permissions.get("defaultAction", "allow")
    )
    rules_in = permissions.get("rules") or []
    rules: List[Dict[str, Any]] = []
    for rule in rules_in:
        if not isinstance(rule, dict):
            raise TypeError("each permissions rule must be a dict")
        entry: Dict[str, Any] = {"action": rule.get("action") or "allow"}
        if rule.get("tool"):
            entry["tool"] = rule["tool"]
        if rule.get("toolbelt"):
            entry["toolbelt"] = rule["toolbelt"]
        if rule.get("match"):
            entry["match"] = rule["match"]
        if "tool" not in entry and "toolbelt" not in entry:
            raise ValueError("each permissions rule requires tool or toolbelt")
        rules.append(entry)
    return {"defaultAction": default_action, "rules": rules}


def serialize_policy_json(permissions: Optional[Dict[str, Any]]) -> str:
    return _json.dumps(normalize_permissions(permissions), separators=(",", ":"))


class Session:
    """A gateway session bound to an ``end_user_id`` and tool policy.

    Create via :meth:`SessionsOperations.create`. Use ``url`` for external
    MCP clients, ``tools()`` for inference ``tools=``, and
    ``handle_tool_calls`` to execute model tool calls over REST.
    """

    def __init__(
        self,
        *,
        session_urn: str,
        end_user_id: str,
        name: str,
        policy: Dict[str, Any],
        gateway_base_url: str,
        tools: ToolsOperations,
        code: CodeOperations,
        provider: BaseProvider,
        raw: Optional[Dict[str, Any]] = None,
    ):
        self.session_urn = session_urn
        self.id = session_urn
        self.end_user_id = end_user_id
        self.name = name
        self.policy = policy
        self._gateway_base_url = gateway_base_url.rstrip("/")
        self.tools = tools
        self.code = code
        self.provider = provider
        self.raw = raw or {}

    @property
    def url(self) -> str:
        """Session-pinned MCP URL for external MCP clients."""
        return session_mcp_url(self._gateway_base_url, self.session_urn)

    def handle_tool_calls(
        self,
        response: Any,
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        """Execute tool calls from an inference response against this session."""
        calls = self.provider.extract_tool_calls(response)
        if not calls:
            return []
        results = execute_tool_calls(calls, self.tools, rationale=rationale)
        return self.provider.format_tool_results(calls, results)

    def execute_tool_calls(
        self,
        calls: Sequence[Any],
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        """Execute pre-extracted tool calls; return raw outputs."""
        return execute_tool_calls(calls, self.tools, rationale=rationale)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Session id={self.session_urn!r} end_user_id={self.end_user_id!r}>"


class SessionsOperations:
    """Create Action Gateway sessions via ``POST /v2/sessions`` on the DO API."""

    def __init__(
        self,
        parent_client: Any,
        *,
        gateway_endpoint: Optional[str] = None,
        provider: Optional[BaseProvider] = None,
    ):
        self._parent = parent_client
        self._gateway_base_url = resolve_gateway_base_url(gateway_endpoint)
        self._provider = provider or default_provider()

    def create(
        self,
        end_user_id: str,
        *,
        name: Optional[str] = None,
        permissions: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """Create a session.

        :param end_user_id: Required end-user identifier bound to the session.
        :param name: Optional display name (auto-generated when omitted).
        :param permissions: Optional policy. When omitted, defaults to
            ``{"defaultAction": "allow", "rules": []}``.
        """
        if not end_user_id or not str(end_user_id).strip():
            raise ValueError("end_user_id is required")

        session_name = name or f"pydo-session-{uuid.uuid4().hex[:8]}"
        policy = normalize_permissions(permissions)
        body = {
            "name": session_name,
            "policy_json": _json.dumps(policy, separators=(",", ":")),
            "end_user_id": str(end_user_id).strip(),
        }

        raw_session = self._post_create(body)
        session_urn = _pick(raw_session, "sessionUrn", "session_urn")
        if not session_urn:
            raise GatewayProtocolError(
                f"session create response missing sessionUrn: {raw_session!r}"
            )

        transport = RESTTransport(
            _BaseURLProxy(self._parent._client, self._gateway_base_url),
            session_id=session_urn,
        )
        tools = ToolsOperations(transport, self._provider)
        code = CodeOperations(transport)
        return Session(
            session_urn=session_urn,
            end_user_id=_pick(raw_session, "endUserId", "end_user_id")
            or str(end_user_id).strip(),
            name=_pick(raw_session, "name") or session_name,
            policy=policy,
            gateway_base_url=self._gateway_base_url,
            tools=tools,
            code=code,
            provider=self._provider,
            raw=raw_session,
        )

    def _post_create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        client = self._parent._client
        request = HttpRequest(
            "POST",
            _SESSIONS_PATH,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=body,
        )
        request.url = client.format_url(request.url)
        pipeline_response = client._pipeline.run(request)
        response = pipeline_response.http_response
        if response.status_code not in (200, 201):
            _raise_gateway_http_error(response)
        payload = _parse_json_body(
            response.text() if hasattr(response, "text") else response.body()
        )
        if not isinstance(payload, dict):
            raise GatewayProtocolError(
                f"unexpected session create response: {payload!r}"
            )
        session = payload.get("session")
        if not isinstance(session, dict):
            raise GatewayProtocolError(
                f"session create response missing session object: {payload!r}"
            )
        return dict(session)


__all__ = [
    "Session",
    "SessionsOperations",
    "normalize_permissions",
    "serialize_policy_json",
]
