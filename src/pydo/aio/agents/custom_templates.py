# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async Hosted Agents sandbox template operations."""

from __future__ import annotations

import json as _json
from typing import Any, Dict, Optional
from urllib.parse import quote

from azure.core.rest import HttpRequest

from pydo.agents.custom_sessions import _OK_STATUS, _raise_agents_http_error
from pydo.agents.custom_templates import _TEMPLATES_PATH
from pydo.custom_extensions import _wrap


def _quote(value: str) -> str:
    return quote(str(value), safe="")


class AsyncTemplatesOperations:
    """Async twin of :class:`~pydo.agents.custom_templates.TemplatesOperations`.

    Does not expose ``GET .../builds/{build_id}/logs``.
    """

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
    ) -> Any:
        """List the caller's team custom sandbox templates."""
        return await self._parse_json(
            await self._send(
                "GET",
                _TEMPLATES_PATH,
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                },
            ),
        )

    async def get(self, template_id: str) -> Any:
        """Get one team sandbox template."""
        return await self._parse_json(
            await self._send("GET", f"{_TEMPLATES_PATH}/{_quote(template_id)}"),
        )

    async def create(self, body: Dict[str, Any]) -> Any:
        """Create a team custom template and kick a build."""
        if not isinstance(body, dict) or not body:
            raise ValueError("body must be a non-empty dict")
        return await self._parse_json(
            await self._send("POST", _TEMPLATES_PATH, body=body),
        )

    async def update(self, template_id: str, body: Dict[str, Any]) -> Any:
        """Update a team template (kicks a new build)."""
        if not isinstance(body, dict) or not body:
            raise ValueError("body must be a non-empty dict")
        return await self._parse_json(
            await self._send(
                "PUT",
                f"{_TEMPLATES_PATH}/{_quote(template_id)}",
                body=body,
            ),
        )

    async def delete(self, template_id: str) -> Any:
        """Delete a team custom template."""
        return await self._parse_json(
            await self._send("DELETE", f"{_TEMPLATES_PATH}/{_quote(template_id)}"),
        )

    async def list_builds(
        self,
        template_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Any:
        """List build history for a template."""
        return await self._parse_json(
            await self._send(
                "GET",
                f"{_TEMPLATES_PATH}/{_quote(template_id)}/builds",
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                },
            ),
        )

    async def get_build(self, template_id: str, build_id: str) -> Any:
        """Get one template build."""
        return await self._parse_json(
            await self._send(
                "GET",
                f"{_TEMPLATES_PATH}/{_quote(template_id)}/builds/{_quote(build_id)}",
            ),
        )
