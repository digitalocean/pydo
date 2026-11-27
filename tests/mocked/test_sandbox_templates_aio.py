# pylint: disable=missing-function-docstring,redefined-outer-name,duplicate-code,missing-class-docstring,too-few-public-methods,unexpected-keyword-arg,unused-argument,unused-variable
"""Mocked tests for async sandbox templates (``pydo.aio.sandbox``).

Fakes the generated operations (honouring ``cls``), like the other async tests.
"""

from types import SimpleNamespace

import pytest

from pydo.aio.sandbox import NotFoundError, SandboxError, Template
from pydo.aio.sandbox import templates as templates_module

pytestmark = pytest.mark.asyncio


def tpl(status="TEMPLATE_STATUS_READY", template_id="t-1"):
    return {
        "template_id": template_id,
        "name": "my-template",
        "status": status,
        "spec": {
            "base_template": "coding-base",
            "image": {"repository": "my-team/my-image", "tag": "v1"},
        },
        "created_at": "2026-11-20T12:00:00Z",
        "updated_at": "2026-11-20T12:05:00Z",
    }


class FakeOperations:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __getattr__(self, name):
        async def run(*args, cls=None, **kwargs):
            self.calls.append((name, args))
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

        monkeypatch.setattr(templates_module, "_make_client", factory)
        return clients

    return make


async def test_create_get_update_delete(install):
    clients = install(
        create_template=[(201, {"template": tpl("TEMPLATE_STATUS_PENDING")})],
        get_template=[(200, {"template": tpl()})],
        update_template=[(200, {"template": tpl("TEMPLATE_STATUS_BUILDING")})],
        delete_template=[(200, {})],
    )
    template = await Template.create(name="my-template", source_oci_ref="r/i:v1")
    assert clients[0].sandboxes.calls[0] == (
        "create_template",
        (
            {
                "name": "my-template",
                "base_template": "coding-base",
                "source_oci_ref": "r/i:v1",
            },
        ),
    )
    assert template.status == "TEMPLATE_STATUS_PENDING"
    assert (await Template.get("t-1")).status == "TEMPLATE_STATUS_READY"
    await template.update(source_oci_ref="r/i:v2")
    assert template.status == "TEMPLATE_STATUS_BUILDING"
    assert clients[0].sandboxes.calls[-1] == (
        "update_template",
        ("t-1", {"source_oci_ref": "r/i:v2"}),
    )
    assert await template.delete() is True
    with pytest.raises(SandboxError, match="source_oci_ref"):
        await template.update()
    await template.close()
    assert clients[0].closed


async def test_validation_and_typed_errors(install):
    install(create_template=[(409, {"id": "conflict", "message": "name collides"})])
    with pytest.raises(SandboxError, match="name"):
        await Template.create(name="", source_oci_ref="r")
    with pytest.raises(TypeError):
        await Template.create(
            name="n", source_oci_ref="r", timeout=1
        )  # pylint: disable=unexpected-keyword-arg
    with pytest.raises(SandboxError, match="name collides") as info:
        await Template.create(name="n", source_oci_ref="r")
    assert info.value.status == 409


async def test_by_id_delete_returns_false_when_gone_and_closes(install):
    clients = install(delete_template=[(404, {"id": "not_found", "message": "gone"})])
    assert await Template.delete("gone") is False
    assert clients[0].closed


async def test_list_pages_and_async_for(install):
    clients = install(
        list_templates=[
            (200, {"templates": [tpl(template_id="a")], "next_page_token": "t2"}),
            (200, {"templates": [tpl(template_id="b")]}),
        ]
    )
    pages = Template.list(limit=1)
    assert [t.template_id async for t in pages] == ["a", "b"]
    assert not pages.has_next
    first, second = clients[0].sandboxes.calls
    assert first == ("list_templates", ())
    await pages.close()
    assert clients[0].closed


async def test_builds_and_failed_wait(install):
    install(
        get_template=[(200, {"template": tpl("TEMPLATE_STATUS_FAILED")})],
        list_template_builds=[
            (
                200,
                {
                    "builds": [
                        {
                            "build_id": "old",
                            "template_id": "t-1",
                            "status": "TEMPLATE_BUILD_STATUS_FAILED",
                            "error": "old",
                            "updated_at": "2026-11-20T10:00:00Z",
                        },
                        {
                            "build_id": "new",
                            "template_id": "t-1",
                            "status": "TEMPLATE_BUILD_STATUS_FAILED",
                            "error": "image not found",
                            "updated_at": "2026-11-20T12:00:00Z",
                        },
                    ]
                },
            )
        ],
        get_template_build=[
            (
                200,
                {
                    "build": {
                        "build_id": "b-1",
                        "template_id": "t-1",
                        "status": "TEMPLATE_BUILD_STATUS_SUCCEEDED",
                    }
                },
            )
        ],
    )
    template = await Template.get("t-1")
    with pytest.raises(SandboxError, match="failed to build: image not found"):
        await template.wait_until_ready()
    assert (await template.build("b-1")).status == "TEMPLATE_BUILD_STATUS_SUCCEEDED"


async def test_wait_until_ready_polls_and_times_out(install):
    install(
        get_template=[
            (200, {"template": tpl("TEMPLATE_STATUS_BUILDING")}),
            (200, {"template": tpl("TEMPLATE_STATUS_BUILDING")}),
            (200, {"template": tpl()}),
        ]
    )
    template = await Template.get("t-1")
    await template.wait_until_ready(poll_interval=0.001)
    assert template.status == "TEMPLATE_STATUS_READY"

    install(get_template=[(200, {"template": tpl("TEMPLATE_STATUS_BUILDING")})])
    template = await Template.get("t-1")
    with pytest.raises(SandboxError, match="not ready in time"):
        await template.wait_until_ready(timeout=0.02, poll_interval=0.001)


async def test_not_found_is_typed(install):
    install(
        get_template=[
            (404, {"id": "not_found", "message": "no such template", "request_id": "r"})
        ]
    )
    with pytest.raises(NotFoundError) as info:
        await Template.get("nope")
    assert info.value.request_id == "r"
