# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async Hosted Agents config operations."""

from __future__ import annotations

import json as _json
from typing import Any, Dict, Optional
from urllib.parse import quote

from azure.core.rest import HttpRequest

from pydo.agents.custom_configs import _CONFIGS_PATH
from pydo.agents.custom_sessions import _OK_STATUS, _raise_agents_http_error
from pydo.custom_extensions import _wrap


def _quote(value: str) -> str:
    return quote(str(value), safe="")


class AsyncConfigsOperations:
    """Async twin of :class:`~pydo.agents.custom_configs.ConfigsOperations`."""

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
        """List active Agent Configs for the caller's team."""
        return await self._parse_json(
            await self._send(
                "GET",
                _CONFIGS_PATH,
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                },
            ),
        )

    async def create(self, body: Dict[str, Any]) -> Any:
        """Create an Agent Config (``POST /v2/agents/configs``)."""
        if not isinstance(body, dict) or not body:
            raise ValueError("body must be a non-empty dict")
        return await self._parse_json(
            await self._send("POST", _CONFIGS_PATH, body=body),
        )

    async def get(self, config_id: str) -> Any:
        """Get an active Agent Config and its sanitized manifest."""
        return await self._parse_json(
            await self._send("GET", f"{_CONFIGS_PATH}/{_quote(config_id)}"),
        )

    async def delete(self, config_id: str) -> None:
        """Soft-delete an Agent Config."""
        await self._send("DELETE", f"{_CONFIGS_PATH}/{_quote(config_id)}")

    async def list_sessions(
        self,
        config_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Any:
        """List sessions created from one Agent Config."""
        return await self._parse_json(
            await self._send(
                "GET",
                f"{_CONFIGS_PATH}/{_quote(config_id)}/sessions",
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                    "status": status,
                },
            ),
        )
