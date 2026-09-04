# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Sync Hosted Agents sandbox template operations (``/v2/agents/templates/...``).

Hand-written against harness-api's public contract
(``public/harness.swagger.json`` / OHS). Preserved across ``make generate``.

Does not expose ``GET .../builds/{build_id}/logs`` (signed URL) — omit that
surface from the client for now.
"""

from __future__ import annotations

import json as _json
from typing import Any, Dict, Optional
from urllib.parse import quote

from azure.core.rest import HttpRequest

from pydo.agents.custom_sessions import _OK_STATUS, _raise_agents_http_error
from pydo.custom_extensions import _wrap

_TEMPLATES_PATH = "/v2/agents/templates"


def _quote(value: str) -> str:
    return quote(str(value), safe="")


class TemplatesOperations:
    """Hosted Agents sandbox template REST operations (team-scoped).

    Covers team custom template CRUD and build history. ``team_id`` is always
    stamped server-side from the authenticated principal — never sent by the
    client. Global catalog templates cannot be deleted via this API.
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
    # Template CRUD
    # ------------------------------------------------------------------

    def list(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Any:
        """List the caller's team custom sandbox templates (keyset-paginated).

        ``GET /v2/agents/templates``
        """
        return self._parse_json(
            self._send(
                "GET",
                _TEMPLATES_PATH,
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                },
            ),
        )

    def get(self, template_id: str) -> Any:
        """Get one team sandbox template.

        ``GET /v2/agents/templates/{template_id}``
        """
        return self._parse_json(
            self._send("GET", f"{_TEMPLATES_PATH}/{_quote(template_id)}"),
        )

    def create(self, body: Dict[str, Any]) -> Any:
        """Create a team custom template and kick a build.

        ``POST /v2/agents/templates``

        Required body fields: ``name``, ``base_template``, ``source_oci_ref``.
        ``base_template`` is a catalog key such as ``coding-base``,
        ``coding-codex``, or ``coding-opencode``.
        """
        if not isinstance(body, dict) or not body:
            raise ValueError("body must be a non-empty dict")
        return self._parse_json(
            self._send("POST", _TEMPLATES_PATH, body=body),
        )

    def update(self, template_id: str, body: Dict[str, Any]) -> Any:
        """Update a team template (kicks a new build).

        ``PUT /v2/agents/templates/{template_id}``

        Optional body fields: ``source_oci_ref``, ``base_template``.
        """
        if not isinstance(body, dict) or not body:
            raise ValueError("body must be a non-empty dict")
        return self._parse_json(
            self._send(
                "PUT",
                f"{_TEMPLATES_PATH}/{_quote(template_id)}",
                body=body,
            ),
        )

    def delete(self, template_id: str) -> Any:
        """Delete a team custom template.

        ``DELETE /v2/agents/templates/{template_id}``

        Returns ``{template_id, deleted}``. Global catalog templates cannot be
        deleted via this API.
        """
        return self._parse_json(
            self._send("DELETE", f"{_TEMPLATES_PATH}/{_quote(template_id)}"),
        )

    # ------------------------------------------------------------------
    # Builds
    # ------------------------------------------------------------------

    def list_builds(
        self,
        template_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Any:
        """List build history for a template (keyset-paginated).

        ``GET /v2/agents/templates/{template_id}/builds``
        """
        return self._parse_json(
            self._send(
                "GET",
                f"{_TEMPLATES_PATH}/{_quote(template_id)}/builds",
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                },
            ),
        )

    def get_build(self, template_id: str, build_id: str) -> Any:
        """Get one template build.

        ``GET /v2/agents/templates/{template_id}/builds/{build_id}``
        """
        return self._parse_json(
            self._send(
                "GET",
                f"{_TEMPLATES_PATH}/{_quote(template_id)}/builds/{_quote(build_id)}",
            ),
        )
