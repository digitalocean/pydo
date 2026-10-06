# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async Hosted Agents workspace operations."""

from __future__ import annotations

import json as _json
from typing import Any, Dict, Optional

from azure.core.rest import HttpRequest

from pydo.agents.custom_sessions import _OK_STATUS, _raise_agents_http_error
from pydo.agents.custom_workspaces import (
    _IDEMPOTENCY_HEADER,
    _WORKSPACES_PATH,
    _create_body,
    _quote,
)
from pydo.custom_extensions import _wrap


class AsyncWorkspacesOperations:
    """Async twin of :class:`~pydo.agents.custom_workspaces.WorkspacesOperations`."""

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

    async def create(
        self,
        size_gibibytes: int,
        *,
        name: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """Create a workspace (``POST /v2/agents/workspaces``).

        See :meth:`pydo.agents.custom_workspaces.WorkspacesOperations.create`.
        """
        headers = {_IDEMPOTENCY_HEADER: idempotency_key} if idempotency_key else None
        return await self._parse_json(
            await self._send(
                "POST",
                _WORKSPACES_PATH,
                body=_create_body(size_gibibytes, name),
                headers=headers,
            ),
        )

    async def list(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Any:
        """List the team's workspaces (keyset-paginated)."""
        return await self._parse_json(
            await self._send(
                "GET",
                _WORKSPACES_PATH,
                params={"page_size": page_size, "page_token": page_token},
            ),
        )

    async def get(self, workspace_id: str) -> Any:
        """Get one workspace."""
        return await self._parse_json(
            await self._send("GET", f"{_WORKSPACES_PATH}/{_quote(workspace_id)}"),
        )

    async def delete(self, workspace_id: str) -> None:
        """Delete a workspace."""
        await self._send("DELETE", f"{_WORKSPACES_PATH}/{_quote(workspace_id)}")
