# pylint: disable=missing-function-docstring,redefined-outer-name
"""Mocked tests for sandbox workspaces (``pydo.sandbox``), through the real pipeline.

The generated client has no workspace operations, so these also cover the raw
``client.send_request`` path.
"""

import json

import pytest
import responses

from pydo.sandbox import (
    ConflictError,
    NotFoundError,
    Sandbox,
    SandboxClient,
    SandboxError,
    ServiceError,
    Workspace,
)

API = "https://sandbox.test"
CONN = {"token": "test-token", "api_url": API}
BASE = API + "/v2/sandboxes/workspaces"


def ws(state="WORKSPACE_STATE_AVAILABLE", workspace_id="ws-1", **extra):
    out = {
        "workspace_id": workspace_id,
        "name": "my-project",
        "size_limit_gib": 10,
        "state": state,
        "attached_sandbox_id": "",
        "last_saved_at": "2026-11-20T12:05:00Z",
        "bytes_used": "2048",
        "created_at": "2026-11-20T12:00:00Z",
    }
    out.update(extra)
    return out


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("DIGITALOCEAN_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("DIGITALOCEAN_API_URL", raising=False)


@pytest.fixture
def rsps():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        yield mock


def body_of(mock, index=-1):
    return json.loads(mock.calls[index].request.body)


def test_create_sends_name_and_size_and_authenticates(rsps):
    rsps.add(
        responses.POST,
        BASE,
        json={"workspace": ws("WORKSPACE_STATE_CREATING")},
        status=201,
    )
    workspace = Workspace.create(name="my-project", size_limit_gib=10, **CONN)
    assert body_of(rsps) == {"name": "my-project", "size_limit_gib": 10}
    assert rsps.calls[0].request.headers["Authorization"] == "Bearer test-token"
    assert (workspace.workspace_id, workspace.name, workspace.state) == (
        "ws-1",
        "my-project",
        "WORKSPACE_STATE_CREATING",
    )
    assert workspace.info.size_limit_gib == 10
    assert workspace.info.bytes_used == 2048
    assert workspace.info.attached_sandbox_id is None
    assert workspace.info.created_at.year == 2026
    assert workspace.info.last_saved_at.minute == 5


def test_create_omits_a_blank_name(rsps):
    rsps.add(responses.POST, BASE, json={"workspace": ws()}, status=201)
    Workspace.create(size_limit_gib=1, **CONN)
    assert body_of(rsps) == {"size_limit_gib": 1}


def test_create_validates_before_sending(rsps):
    for bad in (0, -1, True, "10", None):
        with pytest.raises(SandboxError, match="size_limit_gib"):
            Workspace.create(size_limit_gib=bad, **CONN)
    with pytest.raises(TypeError):
        Workspace.create(name="n")  # pylint: disable=missing-kwoa
    assert len(rsps.calls) == 0


def test_create_raises_typed_errors_from_the_api(rsps):
    rsps.add(
        responses.POST,
        BASE,
        json={"id": "conflict", "message": "team cannot use workspaces"},
        status=409,
    )
    with pytest.raises(ConflictError, match="cannot use workspaces") as info:
        Workspace.create(size_limit_gib=10, **CONN)
    assert (info.value.status, info.value.code) == (409, "conflict")


def test_get_quotes_the_id_and_raises_not_found(rsps):
    rsps.add(responses.GET, BASE + "/ws-1", json={"workspace": ws()})
    assert Workspace.get("ws-1", **CONN).state == "WORKSPACE_STATE_AVAILABLE"
    rsps.add(
        responses.GET,
        BASE + "/nope",
        json={"id": "not_found", "message": "no such workspace", "request_id": "r"},
        status=404,
    )
    with pytest.raises(NotFoundError) as info:
        Workspace.get("nope", **CONN)
    assert info.value.request_id == "r"
    with pytest.raises(SandboxError, match="workspace_id"):
        Workspace.get(" ", **CONN)
    rsps.add(responses.GET, BASE + "/a%2Fb", json={"workspace": ws()})
    Workspace.get("a/b", **CONN)
    assert rsps.calls[-1].request.url.endswith("/workspaces/a%2Fb")


def test_a_non_json_gateway_error_keeps_its_status(rsps):
    rsps.add(
        responses.GET,
        BASE + "/ws-1",
        body="<html>Bad Gateway</html>",
        content_type="text/html",
        status=502,
    )
    with pytest.raises(ServiceError, match="HTTP 502") as info:
        Workspace.get("ws-1", **CONN)
    assert info.value.status == 502


def test_list_walks_every_page_and_filters_by_state(rsps):
    rsps.add(
        responses.GET,
        BASE,
        json={"workspaces": [ws(workspace_id="a")], "next_page_token": "t2"},
    )
    rsps.add(responses.GET, BASE, json={"workspaces": [ws(workspace_id="b")]})
    ids = [
        w.workspace_id
        for w in Workspace.list(state="WORKSPACE_STATE_AVAILABLE", limit=1, **CONN)
    ]
    assert ids == ["a", "b"]
    first, second = (c.request.url for c in rsps.calls)
    assert "page_size=1" in first and "state=WORKSPACE_STATE_AVAILABLE" in first
    assert "page_token" not in first
    assert "page_token=t2" in second


def test_list_one_page_at_a_time(rsps):
    rsps.add(responses.GET, BASE, json={"workspaces": [ws()], "next_page_token": "t2"})
    pages = Workspace.list(**CONN)
    assert [w.workspace_id for w in pages.next_items()] == ["ws-1"]
    assert pages.next_token == "t2"
    assert "page_size" not in rsps.calls[0].request.url


def test_delete_by_id_and_on_the_instance(rsps):
    rsps.add(responses.DELETE, BASE + "/ws-1", json={})
    assert Workspace.delete("ws-1", **CONN) is True
    rsps.add(
        responses.DELETE,
        BASE + "/gone",
        json={"id": "not_found", "message": "gone"},
        status=404,
    )
    assert Workspace.delete("gone", **CONN) is False
    rsps.add(responses.GET, BASE + "/ws-1", json={"workspace": ws()})
    assert Workspace.get("ws-1", **CONN).delete() is True


def test_delete_of_an_attached_workspace_is_a_conflict(rsps):
    rsps.add(
        responses.DELETE,
        BASE + "/ws-1",
        json={"id": "conflict", "message": "workspace is attached"},
        status=409,
    )
    with pytest.raises(ConflictError, match="attached"):
        Workspace.delete("ws-1", **CONN)


def test_refresh_updates_info(rsps):
    rsps.add(
        responses.GET,
        BASE + "/ws-1",
        json={"workspace": ws("WORKSPACE_STATE_CREATING")},
    )
    workspace = Workspace.get("ws-1", **CONN)
    rsps.replace(
        responses.GET,
        BASE + "/ws-1",
        json={"workspace": ws("WORKSPACE_STATE_ATTACHED", attached_sandbox_id="sb-1")},
    )
    assert workspace.refresh().attached_sandbox_id == "sb-1"
    assert workspace.state == "WORKSPACE_STATE_ATTACHED"


def test_wait_until_available_polls_a_creating_workspace(rsps):
    rsps.add(
        responses.GET,
        BASE + "/ws-1",
        json={"workspace": ws("WORKSPACE_STATE_CREATING")},
    )
    workspace = Workspace.get("ws-1", **CONN)
    rsps.replace(responses.GET, BASE + "/ws-1", json={"workspace": ws()})
    workspace.wait_until_available(poll_interval=0.01)
    assert workspace.state == "WORKSPACE_STATE_AVAILABLE"


@pytest.mark.parametrize(
    "state", ["WORKSPACE_STATE_FAILED", "WORKSPACE_STATE_DELETING"]
)
def test_wait_until_available_gives_up_on_a_dead_workspace(rsps, state):
    rsps.add(responses.GET, BASE + "/ws-1", json={"workspace": ws(state)})
    workspace = Workspace.get("ws-1", **CONN)
    with pytest.raises(SandboxError, match="cannot become available"):
        workspace.wait_until_available()
    assert len(rsps.calls) == 1


def test_wait_until_available_times_out(rsps):
    rsps.add(
        responses.GET,
        BASE + "/ws-1",
        json={"workspace": ws("WORKSPACE_STATE_CREATING")},
    )
    workspace = Workspace.get("ws-1", **CONN)
    with pytest.raises(SandboxError, match="not available in time"):
        workspace.wait_until_available(timeout=0.05, poll_interval=0.01)


def test_sandbox_client_binds_options_for_workspaces(rsps):
    rsps.add(
        responses.POST,
        BASE,
        json={"workspace": ws("WORKSPACE_STATE_CREATING")},
        status=201,
    )
    workspace = SandboxClient(**CONN).Workspace.create(size_limit_gib=10)
    assert workspace.workspace_id == "ws-1"


def test_sandbox_create_attaches_a_workspace(rsps):
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes",
        json={
            "sandbox": {
                "sandbox_id": "sb-1",
                "template": "coding-base",
                "state": "SANDBOX_STATE_RUNNING",
            }
        },
        status=201,
    )
    Sandbox.create(workspace_id="ws-1", **CONN)
    assert body_of(rsps)["workspace_id"] == "ws-1"
    Sandbox.create(**CONN)
    assert "workspace_id" not in body_of(rsps)
    with pytest.raises(SandboxError, match="workspace_id"):
        Sandbox.create(workspace_id=" ", **CONN)
