# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Sync Hosted Agents workspace operations (``/v2/agents/workspaces/...``).

A workspace is a saved set of files that outlives individual sessions. Create
one, attach it to a session by passing its ``workspace_id`` at session create
time, and re-attach it to a later session once the first has been destroyed.

Hand-written; preserved across ``make generate``.
"""

from __future__ import annotations

import json as _json
from typing import Any, Dict, Optional
from urllib.parse import quote

from azure.core.rest import HttpRequest

from pydo.agents.custom_sessions import _OK_STATUS, _raise_agents_http_error
from pydo.custom_extensions import _wrap

_WORKSPACES_PATH = "/v2/agents/workspaces"
_IDEMPOTENCY_HEADER = "Idempotency-Key"


def _quote(value: str) -> str:
    return quote(str(value), safe="")


def _create_body(size_gibibytes: int, name: Optional[str]) -> Dict[str, Any]:
    if isinstance(size_gibibytes, bool) or not isinstance(size_gibibytes, int):
        raise ValueError("size_gibibytes must be an integer")
    if size_gibibytes < 1:
        raise ValueError("size_gibibytes must be at least 1")
    body: Dict[str, Any] = {"size_gibibytes": size_gibibytes}
    if name:
        body["name"] = name
    return body


class WorkspacesOperations:
    """Hosted Agents persistent workspace REST operations (team-scoped).

    Responses are returned as the server's envelopes, e.g.
    ``{"workspace": {...}}`` for create/get and
    ``{"workspaces": [...], "next_page_token": "..."}`` for list. The
    workspace ``state`` is exposed as a plain string; compare it against
    :class:`~pydo.agents.custom_models.WorkspaceState` constants.
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

    def create(
        self,
        size_gibibytes: int,
        *,
        name: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """Create a workspace (``POST /v2/agents/workspaces``).

        :param size_gibibytes: Size in GiB (the API accepts 1 to 100).
        :param name: Optional display name.
        :param idempotency_key: Optional ``Idempotency-Key`` header value.
            Retrying with the same key and body within 24 hours returns the
            original workspace (``200``) instead of creating another; the same
            key with a different body is rejected (``422``). The header is
            only sent when a key is given.
        :returns: ``{"workspace": {...}}``. ``201`` for a new workspace, ``200``
            for an idempotent replay. Raises ``ResourceExistsError`` (``409``)
            when the team's workspace limit is reached and ``HttpResponseError``
            for ``501`` when workspaces are not enabled for the team.
        """
        headers = {_IDEMPOTENCY_HEADER: idempotency_key} if idempotency_key else None
        return self._parse_json(
            self._send(
                "POST",
                _WORKSPACES_PATH,
                body=_create_body(size_gibibytes, name),
                headers=headers,
            ),
        )

    def list(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Any:
        """List the team's workspaces (``GET /v2/agents/workspaces``).

        Keyset-paginated: pass the previous response's ``next_page_token`` as
        ``page_token``. ``page_size`` defaults to 50 server-side (max 200). An
        empty ``next_page_token`` marks the last page.

        ``state`` lists only workspaces in that state, one of the
        ``WorkspaceState`` values (for example ``WorkspaceState.AVAILABLE``);
        any other value is a ``400``. A page can hold fewer workspaces than
        ``page_size``, even none, while ``next_page_token`` is not empty, so keep
        requesting pages until it is empty.
        """
        return self._parse_json(
            self._send(
                "GET",
                _WORKSPACES_PATH,
                params={
                    "page_size": page_size,
                    "page_token": page_token,
                    "state": state,
                },
            ),
        )

    def get(self, workspace_id: str) -> Any:
        """Get one workspace (``GET /v2/agents/workspaces/{workspace_id}``).

        Raises ``ResourceNotFoundError`` when it does not exist.
        """
        return self._parse_json(
            self._send("GET", f"{_WORKSPACES_PATH}/{_quote(workspace_id)}"),
        )

    def delete(self, workspace_id: str) -> None:
        """Delete a workspace (``DELETE /v2/agents/workspaces/{workspace_id}``).

        Returns ``204`` with no body. Raises ``ResourceNotFoundError`` (``404``)
        when it does not exist and ``ResourceExistsError`` (``409``) unless the
        workspace is ``AVAILABLE`` or ``FAILED``.
        """
        self._send("DELETE", f"{_WORKSPACES_PATH}/{_quote(workspace_id)}")
