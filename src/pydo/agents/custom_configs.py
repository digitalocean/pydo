# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Sync Hosted Agents config operations (``/v2/agents/configs/...``).

Hand-written against harness-api's public contract
(``public/harness.swagger.json``). Preserved across ``make generate``.
"""

from __future__ import annotations

import json as _json
from typing import Any, Dict, Optional
from urllib.parse import quote

from azure.core.rest import HttpRequest

from pydo.agents.custom_sessions import _OK_STATUS, _raise_agents_http_error
from pydo.custom_extensions import _wrap

_CONFIGS_PATH = "/v2/agents/configs"


def _quote(value: str) -> str:
    return quote(str(value), safe="")


class ConfigsOperations:
    """Hosted Agents Agent Config REST operations (team-scoped).

    Covers durable manifest storage (create/read/list/delete) and listing
    sessions created from a config. Configs are immutable after create — clone
    to a new config to change content.
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
    # Configs CRUD
    # ------------------------------------------------------------------

    def list(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Any:
        """List active Agent Configs for the caller's team.

        Keyset-paginated. Soft-deleted configs are excluded. List items are
        lightweight summaries — use :meth:`get` for the full manifest.
        """
        return self._parse_json(
            self._send(
                "GET",
                _CONFIGS_PATH,
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                },
            ),
        )

    def create(self, body: Dict[str, Any]) -> Any:
        """Create an Agent Config (``POST /v2/agents/configs``).

        Accepts ``name`` and ``manifest_yaml`` (the full ``agents.yaml`` text,
        including write-only ``spec.secrets[].value`` entries for tenant
        secrets). Secret values are stored in Secrets Manager and never echoed
        back. Configs are immutable after create.
        """
        if not isinstance(body, dict) or not body:
            raise ValueError("body must be a non-empty dict")
        return self._parse_json(
            self._send("POST", _CONFIGS_PATH, body=body),
        )

    def get(self, config_id: str) -> Any:
        """Get an active Agent Config and its sanitized manifest."""
        return self._parse_json(
            self._send("GET", f"{_CONFIGS_PATH}/{_quote(config_id)}"),
        )

    def delete(self, config_id: str) -> None:
        """Soft-delete an Agent Config (``DELETE /v2/agents/configs/{id}``).

        Returns ``204`` with no body. Returns ``409`` when any session created
        from this config is still active.
        """
        self._send("DELETE", f"{_CONFIGS_PATH}/{_quote(config_id)}")

    # ------------------------------------------------------------------
    # Sessions from config
    # ------------------------------------------------------------------

    def list_sessions(
        self,
        config_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Any:
        """List sessions created from one Agent Config (keyset-paginated).

        By default destroyed and failed sessions are omitted. Pass
        ``status=SESSION_STATUS_ALL`` to include every session regardless of
        status, or an explicit status to filter.
        """
        return self._parse_json(
            self._send(
                "GET",
                f"{_CONFIGS_PATH}/{_quote(config_id)}/sessions",
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                    "status": status,
                },
            ),
        )
