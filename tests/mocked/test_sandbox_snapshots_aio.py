# pylint: disable=missing-function-docstring,redefined-outer-name,duplicate-code,missing-class-docstring,too-few-public-methods,unexpected-keyword-arg,unused-argument
"""Mocked tests for async sandbox snapshots (``pydo.aio.sandbox``).

Fakes the generated operations (honouring ``cls``), like the other async tests.
"""

from types import SimpleNamespace

import pytest

from pydo.aio.sandbox import (
    NotFoundError,
    SandboxError,
    SandboxTimeoutError,
    Snapshot,
)
from pydo.aio.sandbox import sandbox as sandbox_module
from pydo.aio.sandbox import snapshots as snapshots_module

pytestmark = pytest.mark.asyncio


def snap(state="SNAPSHOT_STATE_COMPLETE", snapshot_id="s-1", **extra):
    out = {
        "snapshot_id": snapshot_id,
        "sandbox_id": "sb-1",
        "name": "my-snapshot",
        "state": state,
        "size_bytes": "1073741824",
        "created_at": "2026-11-20T12:00:00Z",
    }
    out.update(extra)
    return out


class FakeOperations:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __getattr__(self, name):
        async def run(*args, cls=None, **kwargs):
            self.calls.append((name, args, kwargs))
            queue = self.routes[name]
            status, body = queue.pop(0) if len(queue) > 1 else queue[0]
            response = SimpleNamespace(status_code=status, headers={})
            return cls(SimpleNamespace(http_response=response), body, {})

        return run


class FakeClient:
    def __init__(self, routes):
        self.sandboxes = FakeOperations(routes)
        self.closed = False

    async def close(self):
        self.closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()


@pytest.fixture
def install(monkeypatch):
    clients = []

    def make(**routes):
        def factory(token, api_url):
            client = FakeClient(routes)
            clients.append(client)
            return client

        monkeypatch.setattr(snapshots_module, "_make_client", factory)
        monkeypatch.setattr(sandbox_module, "_make_client", factory)
        return clients

    return make


async def test_create_get_delete(install):
    clients = install(
        create_snapshot=[(202, {"snapshot": snap("SNAPSHOT_STATE_CREATING")})],
        get_snapshot=[(200, {"snapshot": snap()})],
        delete_snapshot=[(200, {})],
    )
    snapshot = await Snapshot.create("sb-1", name="my-snapshot", ttl="168h")
    assert clients[0].sandboxes.calls[0][:2] == (
        "create_snapshot",
        ("sb-1", {"name": "my-snapshot", "ttl": "168h"}),
    )
    assert snapshot.state == "SNAPSHOT_STATE_CREATING"
    assert (await Snapshot.get("s-1")).info.size_bytes == 1073741824
    assert await snapshot.delete() is True
    await snapshot.close()
    assert clients[0].closed


async def test_create_without_options_sends_no_body(install):
    clients = install(create_snapshot=[(200, {"snapshot": snap()})])
    await Snapshot.create("sb-1")
    assert clients[0].sandboxes.calls[0][:2] == ("create_snapshot", ("sb-1", None))


async def test_validation_and_typed_errors(install):
    install(create_snapshot=[(404, {"id": "not_found", "message": "no sandbox"})])
    with pytest.raises(SandboxError, match="name"):
        await Snapshot.create("sb-1", name="Bad Name")
    with pytest.raises(SandboxError, match="sandbox_id"):
        await Snapshot.create("")
    with pytest.raises(TypeError):
        await Snapshot.create(
            "sb-1", timeout=1
        )  # pylint: disable=unexpected-keyword-arg
    with pytest.raises(NotFoundError, match="no sandbox"):
        await Snapshot.create("sb-1")


async def test_by_id_delete_returns_false_when_gone_and_closes(install):
    clients = install(delete_snapshot=[(404, {"id": "not_found", "message": "gone"})])
    assert await Snapshot.delete("gone") is False
    assert clients[0].closed


async def test_list_filters_pages_and_async_for(install):
    clients = install(
        list_snapshots=[
            (200, {"snapshots": [snap(snapshot_id="a")], "next_page_token": "t2"}),
            (200, {"snapshots": [snap(snapshot_id="b")]}),
        ]
    )
    pages = Snapshot.list(sandbox_id="sb-1", limit=1)
    assert [s.snapshot_id async for s in pages] == ["a", "b"]
    assert not pages.has_next
    first, second = clients[0].sandboxes.calls
    assert (first[2]["sandbox_id"], first[2]["page_size"], first[2]["page_token"]) == (
        "sb-1",
        1,
        None,
    )
    assert second[2]["page_token"] == "t2"
    await pages.close()
    assert clients[0].closed


async def test_wait_until_ready_polls_and_explains_failures(install):
    install(
        create_snapshot=[(202, {"snapshot": snap("SNAPSHOT_STATE_CREATING")})],
        get_snapshot=[
            (200, {"snapshot": snap("SNAPSHOT_STATE_UPLOADING")}),
            (200, {"snapshot": snap()}),
        ],
    )
    snapshot = await Snapshot.create("sb-1")
    await snapshot.wait_until_ready(poll_interval=0.01)
    assert snapshot.state == "SNAPSHOT_STATE_COMPLETE"

    install(
        create_snapshot=[(202, {"snapshot": snap("SNAPSHOT_STATE_CREATING")})],
        get_snapshot=[
            (
                200,
                {
                    "snapshot": snap(
                        "SNAPSHOT_STATE_FAILED", error_message="disk capture timed out"
                    )
                },
            )
        ],
    )
    failing = await Snapshot.create("sb-1")
    with pytest.raises(SandboxError, match="failed: disk capture timed out"):
        await failing.wait_until_ready(poll_interval=0.01)


async def test_wait_until_ready_times_out(install):
    install(get_snapshot=[(200, {"snapshot": snap("SNAPSHOT_STATE_CREATING")})])
    snapshot = await Snapshot.get("s-1")
    with pytest.raises(SandboxTimeoutError, match="not complete in time"):
        await snapshot.wait_until_ready(timeout=0.05, poll_interval=0.01)


async def test_sandbox_create_snapshot_shares_the_connection(install):
    clients = install(
        create=[
            (
                201,
                {
                    "sandbox": {
                        "sandbox_id": "sb-1",
                        "template": "coding-base",
                        "state": "SANDBOX_STATE_RUNNING",
                        "created_at": "2026-11-20T12:00:00Z",
                    }
                },
            )
        ],
        create_snapshot=[(202, {"snapshot": snap("SNAPSHOT_STATE_CREATING")})],
    )
    from pydo.aio.sandbox import Sandbox  # pylint: disable=import-outside-toplevel

    sandbox = await Sandbox.create(template="coding-base")
    snapshot = await sandbox.create_snapshot(name="before-upgrade")
    assert clients[0].sandboxes.calls[-1][:2] == (
        "create_snapshot",
        ("sb-1", {"name": "before-upgrade"}),
    )
    await snapshot.close()
    assert not clients[0].closed
    with pytest.raises(SandboxError, match="name"):
        await sandbox.create_snapshot(name="Bad Name")
    await sandbox.close()
    assert clients[0].closed
