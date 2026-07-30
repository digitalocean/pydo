# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Sync Hosted Agents trigger operations (``/v2/agents/triggers/...``).

Hand-written against harness-trigger's public contract
(``contracts/trigger.swagger.json``). Preserved across ``make generate``.
"""

from __future__ import annotations

import json as _json
from typing import Any, Dict, Optional
from urllib.parse import quote

from azure.core.rest import HttpRequest

from pydo.agents.custom_sessions import _OK_STATUS, _raise_agents_http_error
from pydo.custom_extensions import _wrap

_TRIGGERS_PATH = "/v2/agents/triggers"
_WEBHOOK_PROVIDERS_PATH = "/v2/agents/webhook-providers"


def _quote(value: str) -> str:
    return quote(str(value), safe="")


class TriggersOperations:
    """Hosted Agents trigger REST operations (team-scoped Config API).

    Covers webhook & cron trigger CRUD, secret rotation, execution history,
    reusable-session listing, and the webhook-provider registry.

    The public webhook ingress
    (``POST /v2/agents/triggers/{id}/webhook``) is intentionally omitted —
    it is authenticated by the per-trigger HMAC secret, not a DO bearer token,
    and is meant for external systems rather than SDK callers.
    """

    def __init__(self, base_url_proxy):
        self._client = base_url_proxy

    def _send(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        headers = {"Accept": "application/json", **(headers or {})}
        kwargs: Dict[str, Any] = {"headers": headers}
        if params:
            kwargs["params"] = {
                k: v for k, v in params.items() if v is not None and v != ""
            }
        if body is not None:
            headers["Content-Type"] = "application/json"
            kwargs["json"] = body

        request = HttpRequest(method, path, **kwargs)
        request.url = self._client.format_url(request.url)
        pipeline_response = self._client._pipeline.run(request, stream=False)
        response = pipeline_response.http_response

        if response.status_code not in _OK_STATUS:
            _raise_agents_http_error(response)
        return pipeline_response

    @staticmethod
    def _parse_json(pipeline_response) -> Any:
        response = pipeline_response.http_response
        body = response.text() if hasattr(response, "text") else response.body()
        if not body:
            return None
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        return _wrap(_json.loads(body))

    # ------------------------------------------------------------------
    # Triggers CRUD
    # ------------------------------------------------------------------

    def list(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        kind: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Any:
        """List the calling team's triggers (``GET /v2/agents/triggers``).

        Keyset-paginated. Soft-deleted triggers are excluded. Optional
        ``kind`` (``webhook`` / ``cron``) and ``status`` (``active`` /
        ``paused``) filters are applied server-side.
        """
        return self._parse_json(
            self._send(
                "GET",
                _TRIGGERS_PATH,
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                    "kind": kind,
                    "status": status,
                },
            ),
        )

    def create(self, body: Dict[str, Any]) -> Any:
        """Create a webhook or cron trigger (``POST /v2/agents/triggers``).

        For webhook triggers the response includes ``webhook_secret`` exactly
        once — it is never returned again. Cron triggers return no secret.

        See the CreateTrigger contract for the conditional-requirement matrix
        (kind/block match, session_mode, output mode, etc.).
        """
        if not isinstance(body, dict) or not body:
            raise ValueError("body must be a non-empty dict")
        return self._parse_json(
            self._send("POST", _TRIGGERS_PATH, body=body),
        )

    def get(self, trigger_id: str) -> Any:
        """Get a single trigger by id (``GET /v2/agents/triggers/{id}``)."""
        return self._parse_json(
            self._send("GET", f"{_TRIGGERS_PATH}/{_quote(trigger_id)}"),
        )

    def update(self, trigger_id: str, body: Dict[str, Any]) -> Any:
        """Partial-update a trigger (``PATCH /v2/agents/triggers/{id}``).

        Only supplied fields change. Pause / re-enable by sending
        ``{"status": "paused"}`` or ``{"status": "active"}``.
        ``kind`` and ``webhook.provider`` are immutable.
        """
        if not isinstance(body, dict) or not body:
            raise ValueError("body must be a non-empty dict")
        return self._parse_json(
            self._send(
                "PATCH",
                f"{_TRIGGERS_PATH}/{_quote(trigger_id)}",
                body=body,
            ),
        )

    def delete(self, trigger_id: str) -> None:
        """Soft-delete a trigger (``DELETE /v2/agents/triggers/{id}``).

        Returns ``204`` with no body. A reuse trigger only unbinds — it never
        destroys the customer's session.
        """
        self._send("DELETE", f"{_TRIGGERS_PATH}/{_quote(trigger_id)}")

    def rotate_secret(self, trigger_id: str) -> Any:
        """Issue a new webhook secret (``POST .../{id}/rotate-secret``).

        Webhook triggers only (``409`` for cron). The new secret is shown
        once; the previous value stays valid briefly for in-flight deliveries.
        """
        return self._parse_json(
            self._send(
                "POST",
                f"{_TRIGGERS_PATH}/{_quote(trigger_id)}/rotate-secret",
            ),
        )

    # ------------------------------------------------------------------
    # Executions
    # ------------------------------------------------------------------

    def list_executions(
        self,
        trigger_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Any:
        """List a trigger's execution history (keyset-paginated).

        Large ``payload`` / ``output_text`` fields are omitted from list items;
        use :meth:`get_execution` to read them.
        """
        return self._parse_json(
            self._send(
                "GET",
                f"{_TRIGGERS_PATH}/{_quote(trigger_id)}/executions",
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                    "status": status,
                },
            ),
        )

    def get_execution(self, trigger_id: str, execution_id: str) -> Any:
        """Get a single execution, including payload and output text."""
        return self._parse_json(
            self._send(
                "GET",
                (
                    f"{_TRIGGERS_PATH}/{_quote(trigger_id)}"
                    f"/executions/{_quote(execution_id)}"
                ),
            ),
        )

    # ------------------------------------------------------------------
    # Lookups & helpers
    # ------------------------------------------------------------------

    def get_by_session(self, session_id: str) -> Any:
        """Reverse-look-up the trigger that produced or binds a session."""
        return self._parse_json(
            self._send(
                "GET",
                f"{_TRIGGERS_PATH}/by-session/{_quote(session_id)}",
            ),
        )

    def list_reusable_sessions(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Any:
        """List the team's PAUSED sessions for the reuse-mode picker."""
        return self._parse_json(
            self._send(
                "GET",
                f"{_TRIGGERS_PATH}/reusable-sessions",
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                },
            ),
        )

    def list_webhook_providers(self) -> Any:
        """List supported webhook providers for the create-trigger UI.

        Static registry (not a database table). Cron triggers have no
        provider and never call this.
        """
        return self._parse_json(self._send("GET", _WEBHOOK_PROVIDERS_PATH))
