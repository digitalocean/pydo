# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async Hosted Agents trigger operations."""

from __future__ import annotations

import json as _json
from typing import Any, Dict, Optional
from urllib.parse import quote

from azure.core.rest import HttpRequest

from pydo.agents.custom_sessions import _OK_STATUS, _raise_agents_http_error
from pydo.agents.custom_triggers import (
    _TRIGGERS_PATH,
    _WEBHOOK_PROVIDERS_PATH,
)
from pydo.custom_extensions import _wrap


def _quote(value: str) -> str:
    return quote(str(value), safe="")


class AsyncTriggersOperations:
    """Async twin of :class:`~pydo.agents.custom_triggers.TriggersOperations`."""

    def __init__(self, base_url_proxy):
        self._client = base_url_proxy

    async def _send(
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
        pipeline_response = await self._client._pipeline.run(request, stream=False)
        response = pipeline_response.http_response

        if response.status_code not in _OK_STATUS:
            await response.read()
            _raise_agents_http_error(response)
        return pipeline_response

    @staticmethod
    async def _parse_json(pipeline_response) -> Any:
        body = await pipeline_response.http_response.read()
        if not body:
            return None
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        return _wrap(_json.loads(body))

    async def list(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        kind: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Any:
        """List the calling team's triggers (``GET /v2/agents/triggers``)."""
        return await self._parse_json(
            await self._send(
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

    async def create(self, body: Dict[str, Any]) -> Any:
        """Create a webhook or cron trigger (``POST /v2/agents/triggers``)."""
        if not isinstance(body, dict) or not body:
            raise ValueError("body must be a non-empty dict")
        return await self._parse_json(
            await self._send("POST", _TRIGGERS_PATH, body=body),
        )

    async def get(self, trigger_id: str) -> Any:
        """Get a single trigger by id."""
        return await self._parse_json(
            await self._send("GET", f"{_TRIGGERS_PATH}/{_quote(trigger_id)}"),
        )

    async def update(self, trigger_id: str, body: Dict[str, Any]) -> Any:
        """Partial-update a trigger (``PATCH /v2/agents/triggers/{id}``)."""
        if not isinstance(body, dict) or not body:
            raise ValueError("body must be a non-empty dict")
        return await self._parse_json(
            await self._send(
                "PATCH",
                f"{_TRIGGERS_PATH}/{_quote(trigger_id)}",
                body=body,
            ),
        )

    async def delete(self, trigger_id: str) -> None:
        """Soft-delete a trigger (``DELETE /v2/agents/triggers/{id}``)."""
        await self._send("DELETE", f"{_TRIGGERS_PATH}/{_quote(trigger_id)}")

    async def rotate_secret(self, trigger_id: str) -> Any:
        """Issue a new webhook secret (shown once)."""
        return await self._parse_json(
            await self._send(
                "POST",
                f"{_TRIGGERS_PATH}/{_quote(trigger_id)}/rotate-secret",
            ),
        )

    async def list_executions(
        self,
        trigger_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Any:
        """List a trigger's execution history."""
        return await self._parse_json(
            await self._send(
                "GET",
                f"{_TRIGGERS_PATH}/{_quote(trigger_id)}/executions",
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                    "status": status,
                },
            ),
        )

    async def get_execution(self, trigger_id: str, execution_id: str) -> Any:
        """Get a single execution, including payload and output text."""
        return await self._parse_json(
            await self._send(
                "GET",
                (
                    f"{_TRIGGERS_PATH}/{_quote(trigger_id)}"
                    f"/executions/{_quote(execution_id)}"
                ),
            ),
        )

    async def get_by_session(self, session_id: str) -> Any:
        """Reverse-look-up the trigger that produced or binds a session."""
        return await self._parse_json(
            await self._send(
                "GET",
                f"{_TRIGGERS_PATH}/by-session/{_quote(session_id)}",
            ),
        )

    async def list_reusable_sessions(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Any:
        """List the team's PAUSED sessions for the reuse-mode picker."""
        return await self._parse_json(
            await self._send(
                "GET",
                f"{_TRIGGERS_PATH}/reusable-sessions",
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                },
            ),
        )

    async def list_webhook_providers(self) -> Any:
        """List supported webhook providers for the create-trigger UI."""
        return await self._parse_json(
            await self._send("GET", _WEBHOOK_PROVIDERS_PATH),
        )
