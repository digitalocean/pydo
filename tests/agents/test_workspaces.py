# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :mod:`pydo.agents.custom_workspaces`."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
)

from pydo.agents import AgentsResources, WorkspaceState

_WORKSPACE = {
    "workspace_id": "ws-1",
    "name": "scratch",
    "state": "AVAILABLE",
    "size_gibibytes": 10,
    "bytes_used": 0,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


class _FakeResponse:
    def __init__(self, status_code: int, body: Any = None):
        self.status_code = status_code
        self.reason = None
        if isinstance(body, (dict, list)):
            self._body_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            self._body_bytes = body.encode("utf-8")
        else:
            self._body_bytes = b""

    def text(self) -> str:
        return self._body_bytes.decode("utf-8")

    def body(self) -> bytes:
        return self._body_bytes

    def read(self) -> bytes:
        return self._body_bytes

    def close(self) -> None:
        pass


class _FakePipeline:
    def __init__(self, responses: List[_FakeResponse]):
        self._responses = list(responses)
        self.calls: List[Any] = []

    def run(self, request, *, stream=False, **kwargs):
        self.calls.append(SimpleNamespace(request=request, stream=stream))
        return SimpleNamespace(http_response=self._responses.pop(0))


def _make_resources(responses: List[_FakeResponse]) -> AgentsResources:
    parent = MagicMock()
    parent._client = MagicMock()
    parent._client._pipeline = _FakePipeline(responses)
    return AgentsResources(parent, agents_endpoint="https://api.digitalocean.com")


def _last_call(resources: AgentsResources):
    return resources._proxy._original._pipeline.calls[-1]


def _path(url: str) -> str:
    return url.split("?", 1)[0]


def _error(code: int, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def test_create_workspace_201():
    resources = _make_resources([_FakeResponse(201, {"workspace": _WORKSPACE})])

    resp = resources.workspaces.create(10, name="scratch")

    call = _last_call(resources)
    assert call.request.method == "POST"
    assert _path(call.request.url).endswith("/v2/agents/workspaces")
    assert call.request.headers.get("Content-Type") == "application/json"
    assert json.loads(call.request.content) == {
        "size_gibibytes": 10,
        "name": "scratch",
    }
    assert resp.workspace.workspace_id == "ws-1"
    assert resp.workspace.state == WorkspaceState.AVAILABLE


def test_create_workspace_omits_name_when_not_given():
    resources = _make_resources([_FakeResponse(201, {"workspace": _WORKSPACE})])

    resources.workspaces.create(5)

    assert json.loads(_last_call(resources).request.content) == {"size_gibibytes": 5}


def test_create_workspace_sends_idempotency_key_only_when_given():
    resources = _make_resources(
        [
            _FakeResponse(201, {"workspace": _WORKSPACE}),
            _FakeResponse(201, {"workspace": _WORKSPACE}),
        ]
    )

    resources.workspaces.create(10)
    assert "Idempotency-Key" not in _last_call(resources).request.headers

    resources.workspaces.create(10, idempotency_key="key-123")
    assert _last_call(resources).request.headers.get("Idempotency-Key") == "key-123"


def test_create_workspace_idempotent_replay_200():
    resources = _make_resources([_FakeResponse(200, {"workspace": _WORKSPACE})])

    resp = resources.workspaces.create(10, idempotency_key="key-123")

    assert resp.workspace.workspace_id == "ws-1"


def test_create_workspace_keeps_unknown_state_as_string():
    ws = dict(_WORKSPACE, state="SOMETHING_NEW")
    resources = _make_resources([_FakeResponse(201, {"workspace": ws})])

    resp = resources.workspaces.create(10)

    assert resp.workspace.state == "SOMETHING_NEW"


@pytest.mark.parametrize("size", [0, -1, "10", 1.5, True, None])
def test_create_workspace_rejects_invalid_size(size):
    resources = _make_resources([])
    with pytest.raises(ValueError, match="size_gibibytes"):
        resources.workspaces.create(size)
    assert not resources._proxy._original._pipeline.calls


def test_list_workspaces_paging_params():
    body = {"workspaces": [_WORKSPACE], "next_page_token": "next"}
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.workspaces.list(page_size=25, page_token="tok")

    call = _last_call(resources)
    assert call.request.method == "GET"
    assert _path(call.request.url).endswith("/v2/agents/workspaces")
    assert "page_size=25" in call.request.url
    assert "page_token=tok" in call.request.url
    assert resp.workspaces[0].workspace_id == "ws-1"
    assert resp.next_page_token == "next"


def test_list_workspaces_state_filter():
    resources = _make_resources(
        [_FakeResponse(200, {"workspaces": [_WORKSPACE], "next_page_token": ""})]
    )

    resp = resources.workspaces.list(state=WorkspaceState.AVAILABLE)

    url = _last_call(resources).request.url
    assert "state=AVAILABLE" in url
    assert "page_size" not in url
    assert "page_token" not in url
    assert resp.workspaces[0].workspace_id == "ws-1"


def test_list_workspaces_state_with_paging():
    resources = _make_resources(
        [_FakeResponse(200, {"workspaces": [], "next_page_token": "next"})]
    )

    resp = resources.workspaces.list(
        page_size=25, page_token="tok", state=WorkspaceState.ATTACHED
    )

    url = _last_call(resources).request.url
    assert "state=ATTACHED" in url
    assert "page_size=25" in url
    assert "page_token=tok" in url
    # A page can be empty while more follow.
    assert resp.workspaces == []
    assert resp.next_page_token == "next"


def test_list_workspaces_without_params_sends_no_query():
    resources = _make_resources(
        [_FakeResponse(200, {"workspaces": [], "next_page_token": ""})]
    )

    resources.workspaces.list()

    assert "?" not in _last_call(resources).request.url


def test_get_workspace():
    resources = _make_resources([_FakeResponse(200, {"workspace": _WORKSPACE})])

    resp = resources.workspaces.get("ws-1")

    call = _last_call(resources)
    assert call.request.method == "GET"
    assert _path(call.request.url).endswith("/v2/agents/workspaces/ws-1")
    assert resp.workspace.size_gibibytes == 10


def test_get_workspace_escapes_id():
    resources = _make_resources([_FakeResponse(200, {"workspace": _WORKSPACE})])

    resources.workspaces.get("a/b")

    assert _path(_last_call(resources).request.url).endswith(
        "/v2/agents/workspaces/a%2Fb"
    )


def test_delete_workspace():
    resources = _make_resources([_FakeResponse(204)])

    assert resources.workspaces.delete("ws-1") is None

    call = _last_call(resources)
    assert call.request.method == "DELETE"
    assert _path(call.request.url).endswith("/v2/agents/workspaces/ws-1")


def test_get_workspace_404():
    resources = _make_resources(
        [_FakeResponse(404, _error(404, "workspace not found"))]
    )
    with pytest.raises(ResourceNotFoundError):
        resources.workspaces.get("missing")


def test_delete_workspace_404():
    resources = _make_resources(
        [_FakeResponse(404, _error(404, "workspace not found"))]
    )
    with pytest.raises(ResourceNotFoundError):
        resources.workspaces.delete("missing")


def test_delete_workspace_409_when_not_available():
    resources = _make_resources(
        [_FakeResponse(409, _error(409, "workspace is not AVAILABLE or FAILED"))]
    )
    with pytest.raises(ResourceExistsError) as excinfo:
        resources.workspaces.delete("ws-1")
    assert "not AVAILABLE or FAILED" in str(excinfo.value)


def test_create_workspace_409_team_limit():
    resources = _make_resources([_FakeResponse(409, _error(409, "workspace limit"))])
    with pytest.raises(ResourceExistsError):
        resources.workspaces.create(10)


def test_create_workspace_422_idempotency_conflict():
    resources = _make_resources(
        [_FakeResponse(422, _error(422, "idempotency key reused with a new body"))]
    )
    with pytest.raises(HttpResponseError) as excinfo:
        resources.workspaces.create(20, idempotency_key="key-123")
    assert excinfo.value.status_code == 422
    assert "idempotency key" in str(excinfo.value)


def test_create_workspace_501_not_enabled():
    resources = _make_resources(
        [_FakeResponse(501, _error(501, "workspaces are not enabled"))]
    )
    with pytest.raises(HttpResponseError) as excinfo:
        resources.workspaces.create(10)
    assert excinfo.value.status_code == 501
    assert "workspaces are not enabled" in str(excinfo.value)


def test_workspace_401():
    resources = _make_resources([_FakeResponse(401, _error(401, "unauthorized"))])
    with pytest.raises(ClientAuthenticationError):
        resources.workspaces.list()


# ---------------------------------------------------------------------------
# workspace_id on session create
# ---------------------------------------------------------------------------


def test_create_session_from_config_sends_workspace_id_in_body():
    resources = _make_resources(
        [_FakeResponse(200, {"session": {"session_id": "s-1", "workspace_id": "ws-1"}})]
    )

    resp = resources.sessions.create_from_config(
        name="run-1", config_id="cfg-1", workspace_id="ws-1"
    )

    call = _last_call(resources)
    assert call.request.headers.get("Content-Type") == "application/json"
    assert json.loads(call.request.content) == {
        "name": "run-1",
        "config_id": "cfg-1",
        "workspace_id": "ws-1",
    }
    assert "workspace_id" not in call.request.url
    assert resp.session.workspace_id == "ws-1"


def test_create_session_from_config_omits_workspace_id_by_default():
    resources = _make_resources([_FakeResponse(200, {"session": {"session_id": "s"}})])

    resources.sessions.create_from_config(name="run-1", config_id="cfg-1")

    assert json.loads(_last_call(resources).request.content) == {
        "name": "run-1",
        "config_id": "cfg-1",
    }


def test_create_session_from_manifest_has_no_workspace_id():
    manifest = "kind: Agent\nmetadata:\n  name: demo\n"
    resources = _make_resources([_FakeResponse(200, {"session": {"session_id": "s"}})])

    with pytest.raises(TypeError):
        resources.sessions.create_from_manifest(manifest, workspace_id="ws-1")

    resources.sessions.create_from_manifest(manifest)

    call = _last_call(resources)
    assert call.request.headers.get("Content-Type") == "application/x-yaml"
    assert "workspace_id" not in call.request.url


def test_start_has_no_workspace_id():
    resources = _make_resources([_FakeResponse(200, {"session": {"session_id": "s"}})])

    with pytest.raises(TypeError):
        resources.start("kind: Agent\n", workspace_id="ws-1")

    resources.start("kind: Agent\n")

    assert "workspace_id" not in _last_call(resources).request.url


@pytest.mark.parametrize("status", [409, 501])
def test_create_session_workspace_errors(status):
    resources = _make_resources([_FakeResponse(status, _error(status, "nope"))])
    expected = ResourceExistsError if status == 409 else HttpResponseError
    with pytest.raises(expected):
        resources.sessions.create_from_config(
            name="run-1", config_id="cfg-1", workspace_id="ws-1"
        )
