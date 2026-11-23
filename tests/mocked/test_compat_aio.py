# pylint: disable=missing-function-docstring,redefined-outer-name,protected-access
"""Mocked tests for the async compat clients (E2B, Daytona, Modal ``.aio``).

Fakes the generated operations and the client's pipeline, like the other async
sandbox tests, so the compat layer's own logic is covered without a network.
"""

import pytest

from pydo.aio.sandbox import sandbox as sandbox_module
from pydo.aio.sandbox.compat import daytona as aio_daytona
from pydo.aio.sandbox.compat import e2b as aio_e2b
from pydo.sandbox import SandboxNotImplementedError
from pydo.sandbox.compat import modal

from .test_sandbox_commands_aio import RAW, FakeClient, FakeStreamResponse, b64, line

pytestmark = pytest.mark.asyncio

PAUSED = dict(RAW, state="SANDBOX_STATE_PAUSED")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("DIGITALOCEAN_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("DIGITALOCEAN_API_URL", raising=False)


@pytest.fixture
def install(monkeypatch):
    def make(stream=None, **routes):
        client = FakeClient(
            {
                "create": (201, {"sandbox": RAW}),
                "get": (200, {"sandbox": RAW}),
                "delete": (200, {}),
                "post_pause": (200, {"sandbox": PAUSED}),
                "post_resume": (200, {"sandbox": RAW}),
                **routes,
            },
            stream,
        )
        monkeypatch.setattr(
            sandbox_module, "_make_client", lambda token, api_url: client
        )
        return client

    return make


def run_stream(code=0, out="hello\n"):
    return FakeStreamResponse(
        200,
        [
            line({"stdout": b64(out)}),
            line({"stderr": b64("e\n")}),
            line({"exit": {"exit_code": code}}),
        ],
    )


def names(client):
    return [call[0] for call in client.sandboxes.calls]


# E2B ---------------------------------------------------------------------


async def test_e2b_create_run_pause_and_kill(install):
    client = install(stream=run_stream(), create_command=(200, {"pid": 4}))
    sandbox = await aio_e2b.E2bClient(api_key="t").AsyncSandbox.create(
        template="coding-base", envs={"A": "1"}
    )
    assert client.sandboxes.calls[0][1] == (
        {
            "template": "coding-base",
            "size_slug": "mars-2vcpu-4gb",
            "env_vars": {"A": "1"},
        },
    )
    seen = []
    result = await sandbox.commands.run("echo hello", on_stdout=seen.append)
    assert (result.stdout, result.stderr, result.exit_code) == (
        "hello\n",
        "e\n",
        0,
    ) and seen == ["hello\n"]
    assert await sandbox.pause() is True
    assert await sandbox.kill() is True
    assert names(client)[-2:] == ["post_pause", "delete"]


async def test_e2b_non_zero_exit_raises_like_e2b(install):
    install(stream=run_stream(code=5), create_command=(200, {"pid": 4}))
    sandbox = await aio_e2b.AsyncSandbox.create()
    with pytest.raises(aio_e2b.CommandExitException) as err:
        await sandbox.commands.run("false")
    assert err.value.exit_code == 5


async def test_e2b_background_handle_and_refusals(install):
    install(stream=run_stream(), create_command=(200, {"pid": 4}))
    sandbox = await aio_e2b.AsyncSandbox.create()
    handle = await sandbox.commands.run("sleep 1", background=True)
    assert handle.pid == 4 and (await handle.wait()).stdout == "hello\n"
    with pytest.raises(SandboxNotImplementedError, match="AsyncSandbox.create"):
        await aio_e2b.AsyncSandbox.create(timeout=5)
    with pytest.raises(SandboxNotImplementedError, match="AsyncFilesystem.read"):
        await sandbox.files.read("/a")


async def test_e2b_connect_resumes_and_not_found_is_an_e2b_exception(install):
    client = install(get=(200, {"sandbox": PAUSED}))
    sandbox = await aio_e2b.AsyncSandbox.connect("sb-1")
    assert sandbox.sandbox_id == "sb-1" and "post_resume" in names(client)
    install(get=(404, {"id": "not_found", "message": "gone"}))
    with pytest.raises(aio_e2b.NotFoundException):
        await aio_e2b.AsyncSandbox.connect("missing")


async def test_e2b_list_pages(install):
    install(list=(200, {"sandboxes": [RAW], "next_page_token": "t2"}))
    paginator = aio_e2b.AsyncSandbox.list(limit=1)
    assert paginator.has_next
    items = await paginator.next_items()
    assert [i.sandbox_id for i in items] == ["sb-1"] and paginator.next_token == "t2"


# Daytona -----------------------------------------------------------------


async def test_daytona_v0_create_exec_stop_delete(install):
    client = install(stream=run_stream(code=2), create_command=(200, {"pid": 4}))
    async with aio_daytona.AsyncDaytona(
        aio_daytona.DaytonaConfig(api_key="t")
    ) as daytona:
        sandbox = await daytona.create(
            aio_daytona.CreateSandboxFromSnapshotParams(
                snapshot="my-snap", network_block_all=True
            )
        )
        assert client.sandboxes.calls[0][1] == (
            {
                "template": "my-snap",
                "size_slug": "mars-2vcpu-4gb",
                "allow_internet_access": False,
            },
        )
        result = await sandbox.process.exec("make")
        assert result.exit_code == 2 and result.result == "hello\ne\n"
        await daytona.stop(sandbox)
        assert sandbox.state == aio_daytona.SandboxState.STOPPED
        await daytona.start(sandbox)
        await daytona.delete(sandbox)
    assert names(client)[-1] == "delete"


async def test_daytona_v0_refuses_and_lists(install):
    install(list=(200, {"sandboxes": [RAW]}))
    daytona = aio_daytona.AsyncDaytona(aio_daytona.DaytonaConfig(api_key="t"))
    with pytest.raises(SandboxNotImplementedError, match="AsyncDaytona.create"):
        await daytona.create(
            aio_daytona.CreateSandboxFromImageParams(image="python:3.12")
        )
    with pytest.raises(SandboxNotImplementedError, match="not supported"):
        aio_daytona.AsyncDaytona(aio_daytona.DaytonaConfig(api_key="t", target="us"))
    found = [s.id async for s in await daytona.list()]
    assert found == ["sb-1"]


async def test_daytona_v2_create_from_snapshot_and_exec(install):
    client = install(stream=run_stream(), create_command=(200, {"pid": 4}))
    daytona = aio_daytona.AsyncDaytona(aio_daytona.DaytonaConfig(api_key="t"))
    sandbox = await daytona.v2.create_from_snapshot("my-snap")
    assert client.sandboxes.calls[0][1][0]["template"] == "my-snap"
    result = await sandbox.exec("echo hello")
    assert result.stdout == "hello\n" and result.reason == "exited"
    await daytona.v2.pause(sandbox)
    with pytest.raises(SandboxNotImplementedError, match="AsyncFileSystemService"):
        await sandbox.fs.read_text("/a")


# Modal .aio ----------------------------------------------------------------


async def test_modal_aio_create_exec_read_terminate(install):
    client = install(stream=run_stream(code=3), create_command=(200, {"pid": 4}))
    box = await modal.ModalClient(token_secret="t").Sandbox.create.aio(
        cpu=1, memory=1024, env={"A": "1"}
    )
    assert client.sandboxes.calls[0][1] == (
        {
            "template": "coding-base",
            "size_slug": "mars-1vcpu-1gb",
            "env_vars": {"A": "1"},
        },
    )
    process = await box.exec.aio("echo", "hello")
    assert await process.stdout.read.aio() == "hello\n"
    assert await process.stderr.read.aio() == "e\n"
    assert await process.wait.aio() == 3
    assert await box.terminate.aio() is None
    assert names(client)[-1] == "delete"


async def test_modal_aio_stdout_iterates_asynchronously(install):
    install(stream=run_stream(out="a\nb\n"), create_command=(200, {"pid": 4}))
    box = await modal.ModalClient(token_secret="t").Sandbox.create.aio()
    process = await box.exec.aio("cmd")
    lines = [chunk async for chunk in process.stdout]
    assert lines == ["a\n", "b\n"]


async def test_modal_aio_refusals_and_the_blocking_call_on_an_async_sandbox(install):
    install(stream=run_stream(), create_command=(200, {"pid": 4}))
    client = modal.ModalClient(token_secret="t")
    with pytest.raises(SandboxNotImplementedError, match="Modal.Sandbox.create"):
        await client.Sandbox.create.aio(timeout=900)
    box = await client.Sandbox.create.aio()
    with pytest.raises(modal.exception.Error, match="async API"):
        box.terminate()
    with pytest.raises(SandboxNotImplementedError, match="Sandbox.tunnels"):
        await box.tunnels.aio()
    install(list=(200, {"sandboxes": [RAW]}))
    found = [s async for s in client.Sandbox.list.aio()]
    assert [s.object_id for s in found] == ["sb-1"]
