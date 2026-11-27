# pylint: disable=missing-function-docstring,redefined-outer-name
"""Mocked tests for async sandbox workspaces (``pydo.aio.sandbox``).

Runs through the real async pipeline, with aioresponses.
"""

import json
import re

import pytest
from aioresponses import aioresponses

from pydo.aio.sandbox import (
    ConflictError,
    NotFoundError,
    Sandbox,
    SandboxClient,
    SandboxError,
    ServiceError,
    Workspace,
)

pytestmark = pytest.mark.asyncio

API = "https://sandbox.test"
CONN = {"token": "test-token", "api_url": API}
BASE = API + "/v2/sandboxes/workspaces"


def route(suffix=""):
    return re.compile(rf"^{re.escape(BASE)}{suffix}(\?.*)?$")


def ws(state="WORKSPACE_STATE_AVAILABLE", workspace_id="ws-1", **extra):
    out = {
        "workspace_id": workspace_id,
        "name": "my-project",
        "size_limit_gib": 10,
        "state": state,
        "created_at": "2026-11-20T12:00:00Z",
    }
    out.update(extra)
    return out


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("DIGITALOCEAN_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("DIGITALOCEAN_API_URL", raising=False)


@pytest.fixture
def mock():
    with aioresponses() as m:
        yield m


def request_of(mock, method, url_re):
    for (m, url), calls in mock.requests.items():
        if m == method and url_re.match(str(url)):
            return calls[-1]
    raise AssertionError("no %s request to %s" % (method, url_re.pattern))


async def test_create_sends_name_and_size(mock):
    mock.post(
        route(), payload={"workspace": ws("WORKSPACE_STATE_CREATING")}, status=201
    )
    async with await Workspace.create(
        name="my-project", size_limit_gib=10, **CONN
    ) as workspace:
        call = request_of(mock, "POST", route())
        assert json.loads(call.kwargs["data"]) == {
            "name": "my-project",
            "size_limit_gib": 10,
        }
        assert call.kwargs["headers"]["Authorization"] == "Bearer test-token"
        assert (workspace.workspace_id, workspace.state) == (
            "ws-1",
            "WORKSPACE_STATE_CREATING",
        )


async def test_create_validates_and_raises_typed_errors(mock):
    with pytest.raises(SandboxError, match="size_limit_gib"):
        await Workspace.create(size_limit_gib=0, **CONN)
    mock.post(
        route(),
        payload={"id": "conflict", "message": "team cannot use workspaces"},
        status=409,
    )
    with pytest.raises(ConflictError, match="cannot use workspaces") as info:
        await Workspace.create(size_limit_gib=10, **CONN)
    assert info.value.status == 409


async def test_get_and_not_found(mock):
    mock.get(route("/ws-1"), payload={"workspace": ws()})
    workspace = await Workspace.get("ws-1", **CONN)
    assert workspace.state == "WORKSPACE_STATE_AVAILABLE"
    await workspace.close()
    mock.get(
        route("/nope"),
        payload={"id": "not_found", "message": "no such workspace"},
        status=404,
    )
    with pytest.raises(NotFoundError):
        await Workspace.get("nope", **CONN)


async def test_a_non_json_gateway_error_keeps_its_status(mock):
    mock.get(
        route("/ws-1"),
        body="<html>Bad Gateway</html>",
        content_type="text/html",
        status=502,
        repeat=True,  # the pipeline retries a 502
    )
    with pytest.raises(ServiceError, match="HTTP 502"):
        await Workspace.get("ws-1", **CONN)


async def test_list_pages_and_async_for(mock):
    mock.get(
        route(),
        payload={"workspaces": [ws(workspace_id="a")], "next_page_token": "t2"},
    )
    mock.get(route(), payload={"workspaces": [ws(workspace_id="b")]})
    pages = Workspace.list(state="WORKSPACE_STATE_AVAILABLE", limit=1, **CONN)
    assert [w.workspace_id async for w in pages] == ["a", "b"]
    assert not pages.has_next
    urls = [str(url) for (_, url) in mock.requests]
    assert "state=WORKSPACE_STATE_AVAILABLE" in urls[0]
    assert "page_size=1" in urls[0]
    assert any("page_token=t2" in u for u in urls)
    await pages.close()


async def test_delete_by_id_and_on_the_instance(mock):
    mock.delete(route("/ws-1"), payload={})
    assert await Workspace.delete("ws-1", **CONN) is True
    mock.delete(
        route("/gone"), payload={"id": "not_found", "message": "gone"}, status=404
    )
    assert await Workspace.delete("gone", **CONN) is False
    mock.get(route("/ws-1"), payload={"workspace": ws()})
    mock.delete(route("/ws-1"), payload={})
    async with await Workspace.get("ws-1", **CONN) as workspace:
        assert await workspace.delete() is True


async def test_wait_until_available_polls_fails_and_times_out(mock):
    mock.get(route("/ws-1"), payload={"workspace": ws("WORKSPACE_STATE_CREATING")})
    mock.get(route("/ws-1"), payload={"workspace": ws()})
    workspace = await Workspace.get("ws-1", **CONN)
    await workspace.wait_until_available(poll_interval=0.001)
    assert workspace.state == "WORKSPACE_STATE_AVAILABLE"
    await workspace.close()

    mock.get(
        route("/ws-2"),
        payload={"workspace": ws("WORKSPACE_STATE_FAILED", workspace_id="ws-2")},
    )
    failed = await Workspace.get("ws-2", **CONN)
    with pytest.raises(SandboxError, match="cannot become available"):
        await failed.wait_until_available()
    await failed.close()

    mock.get(
        route("/ws-3"),
        payload={"workspace": ws("WORKSPACE_STATE_CREATING", workspace_id="ws-3")},
        repeat=True,
    )
    slow = await Workspace.get("ws-3", **CONN)
    with pytest.raises(SandboxError, match="not available in time"):
        await slow.wait_until_available(timeout=0.05, poll_interval=0.01)
    await slow.close()


async def test_sandbox_client_binds_options_and_sandbox_attaches_a_workspace(mock):
    mock.post(route(), payload={"workspace": ws()}, status=201)
    workspace = await SandboxClient(**CONN).Workspace.create(size_limit_gib=10)
    assert workspace.workspace_id == "ws-1"
    await workspace.close()

    sandbox_route = re.compile(rf"^{re.escape(API)}/v2/sandboxes$")
    mock.post(
        sandbox_route,
        payload={
            "sandbox": {
                "sandbox_id": "sb-1",
                "template": "coding-base",
                "state": "SANDBOX_STATE_RUNNING",
            }
        },
        status=201,
    )
    sandbox = await Sandbox.create(workspace_id="ws-1", **CONN)
    call = request_of(mock, "POST", sandbox_route)
    assert json.loads(call.kwargs["data"])["workspace_id"] == "ws-1"
    await sandbox.close()
