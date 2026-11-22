# pylint: disable=missing-function-docstring,redefined-outer-name,protected-access
"""Mocked tests for the async Sandbox SDK (``pydo.aio.sandbox``).

The sync tests run the real generated pipeline. These swap the generated
``client.sandboxes`` operations for a fake that honours the ``cls`` callback,
so the async facade's own logic (status handling, paging, cleanup) is covered
without a network.
"""

from types import SimpleNamespace

import pytest

from pydo.aio.sandbox import (
    NotFoundError,
    Sandbox,
    SandboxClient,
    SandboxError,
)
from pydo.aio.sandbox import sandbox as sandbox_module

pytestmark = pytest.mark.asyncio


def raw(sandbox_id, state="SANDBOX_STATE_RUNNING"):
    return {
        "sandbox_id": sandbox_id,
        "template": "coding-base",
        "state": state,
        "size_slug": "mars-2vcpu-4gb",
        "created_at": "2026-11-20T12:00:00Z",
    }


class FakeOperations:
    """Answers each operation from ``routes[name]``, a list of ``(status, body)``."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def _op(self, name):
        async def run(*args, cls=None, **kwargs):
            self.calls.append((name, args, kwargs))
            queue = self.routes[name]
            status, body = queue.pop(0) if len(queue) > 1 else queue[0]
            response = SimpleNamespace(status_code=status, headers={})
            return cls(SimpleNamespace(http_response=response), body, {})

        return run

    def __getattr__(self, name):
        return self._op(name)


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
def fake(monkeypatch):
    clients = []

    def install(routes):
        def make(token, api_url):
            client = FakeClient(routes)
            clients.append(client)
            return client

        monkeypatch.setattr(sandbox_module, "_make_client", make)
        return clients

    return install


async def test_create_pause_resume_kill(fake):
    clients = fake(
        {
            "create": [(201, {"sandbox": raw("sb-1")})],
            "post_pause": [(200, {"sandbox": raw("sb-1", "SANDBOX_STATE_PAUSED")})],
            "post_resume": [(200, {"sandbox": raw("sb-1")})],
            "delete": [(200, {})],
        }
    )
    sb = await Sandbox.create(template="coding-base")
    assert clients[0].sandboxes.calls[0][1] == (
        {"template": "coding-base", "size_slug": "mars-2vcpu-4gb"},
    )
    assert (await sb.pause()).state == "SANDBOX_STATE_PAUSED"
    await sb.resume()
    assert sb.state == "SANDBOX_STATE_RUNNING"
    assert await sb.kill() is True
    await sb.close()
    assert clients[0].closed


async def test_by_id_kill_returns_false_when_gone_and_closes(fake):
    clients = fake({"delete": [(404, {"id": "not_found", "message": "gone"})]})
    assert await Sandbox.kill("gone") is False
    assert clients[0].closed


async def test_by_id_pause(fake):
    fake({"post_pause": [(200, {"sandbox": raw("sb-2", "SANDBOX_STATE_PAUSED")})]})
    assert (await Sandbox.pause("sb-2")).state == "SANDBOX_STATE_PAUSED"


async def test_connect_resumes_a_paused_sandbox(fake):
    fake(
        {
            "get": [(200, {"sandbox": raw("sb-1", "SANDBOX_STATE_PAUSED")})],
            "post_resume": [(200, {"sandbox": raw("sb-1")})],
        }
    )
    assert (await Sandbox.connect("sb-1")).state == "SANDBOX_STATE_RUNNING"


async def test_list_pages_and_async_for(fake):
    clients = fake(
        {
            "list": [
                (200, {"sandboxes": [raw("a")], "next_page_token": "t2"}),
                (200, {"sandboxes": [raw("b")]}),
            ]
        }
    )
    pages = Sandbox.list(limit=1, state="SANDBOX_STATE_RUNNING")
    assert [s.sandbox_id async for s in pages] == ["a", "b"]
    first, second = clients[0].sandboxes.calls
    assert {k: v for k, v in first[2].items() if k != "raw_response_hook"} == {
        "page_size": 1,
        "page_token": None,
        "state": "SANDBOX_STATE_RUNNING",
    }
    assert second[2]["page_token"] == "t2"
    assert not pages.has_next
    await pages.close()


async def test_list_one_page_at_a_time(fake):
    fake({"list": [(200, {"sandboxes": [raw("a")], "next_page_token": "t2"})]})
    pages = Sandbox.list()
    assert pages.has_next
    assert [s.sandbox_id for s in await pages.next_items()] == ["a"]
    assert pages.next_token == "t2"


async def test_errors_are_typed_even_when_the_generated_op_returns_the_body(fake):
    fake(
        {
            "create": [
                (
                    404,
                    {
                        "id": "not_found",
                        "message": "Template not found.",
                        "request_id": "r",
                    },
                )
            ]
        }
    )
    with pytest.raises(NotFoundError) as info:
        await Sandbox.create(template="nope")
    assert info.value.status == 404
    assert info.value.code == "not_found"
    assert info.value.request_id == "r"


async def test_create_closes_the_client_when_it_fails(fake):
    clients = fake({"create": [(409, {"id": "conflict", "message": "x"})]})
    with pytest.raises(SandboxError):
        await Sandbox.create(template="coding-base")
    assert clients[0].closed


async def test_options_are_validated_before_sending(fake):
    clients = fake({})
    with pytest.raises(SandboxError, match="template"):
        await Sandbox.create(template="")
    with pytest.raises(TypeError):
        await Sandbox.create(
            template="coding-base", timeout=5
        )  # pylint: disable=unexpected-keyword-arg
    assert not clients


async def test_async_with_kills_and_closes(fake):
    clients = fake({"create": [(201, {"sandbox": raw("sb-1")})], "delete": [(200, {})]})
    async with await SandboxClient(token="t").Sandbox.create(
        template="coding-base"
    ) as sb:
        assert sb.sandbox_id == "sb-1"
    assert clients[0].sandboxes.calls[-1][0] == "delete"
    assert clients[0].closed


async def test_wait_until_running_polls(fake):
    fake(
        {
            "get": [
                (200, {"sandbox": raw("sb-1", "SANDBOX_STATE_CREATING")}),
                (200, {"sandbox": raw("sb-1")}),
            ]
        }
    )
    sb = await Sandbox.get("sb-1")
    await sb.wait_until_running(poll_interval=0.001)
    assert sb.state == "SANDBOX_STATE_RUNNING"
