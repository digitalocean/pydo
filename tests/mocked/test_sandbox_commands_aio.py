# pylint: disable=missing-function-docstring,redefined-outer-name,protected-access
"""Mocked tests for async sandbox commands (``pydo.aio.sandbox``).

Fakes the generated operations (honouring ``cls``) and the client's pipeline, so
the async facade's own logic is covered without a network.
"""

import base64
import json
from types import SimpleNamespace

import pytest

from pydo.aio.sandbox import NotFoundError, Sandbox, SandboxError
from pydo.aio.sandbox import sandbox as sandbox_module

pytestmark = pytest.mark.asyncio

ID = "sb-1"
RAW = {
    "sandbox_id": ID,
    "template": "coding-base",
    "state": "SANDBOX_STATE_RUNNING",
    "size_slug": "mars-2vcpu-4gb",
    "created_at": "2026-11-20T12:00:00Z",
}


def b64(text):
    return base64.b64encode(text if isinstance(text, bytes) else text.encode()).decode()


def line(result):
    return json.dumps({"result": result}) + "\n"


class FakeOperations:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __getattr__(self, name):
        async def run(*args, cls=None, **kwargs):
            self.calls.append((name, args))
            status, body = self.routes[name]
            response = SimpleNamespace(status_code=status, headers={})
            return cls(SimpleNamespace(http_response=response), body, {})

        return run


class FakeStreamResponse:
    def __init__(self, status, chunks=(), body=None):
        self.status_code = status
        self.headers = {}
        self._chunks = chunks
        self._body = body
        self.closed = False

    async def read(self):
        return b""

    def json(self):
        return self._body

    async def iter_bytes(self):
        for chunk in self._chunks:
            yield chunk.encode() if isinstance(chunk, str) else chunk

    async def close(self):
        self.closed = True


class FakeClient:
    def __init__(self, routes, stream):
        self.sandboxes = FakeOperations(routes)
        self.stream = stream
        self.requested = []

        async def run(request, stream=False):
            self.requested.append((request.url, stream))
            return SimpleNamespace(http_response=self.stream)

        self._client = SimpleNamespace(
            format_url=lambda url: "https://sandbox.test" + url,
            _pipeline=SimpleNamespace(run=run),
        )

    async def close(self):
        pass


@pytest.fixture
def install(monkeypatch):
    def make(stream=None, **routes):
        client = FakeClient({"get": (200, {"sandbox": RAW}), **routes}, stream)
        monkeypatch.setattr(
            sandbox_module, "_make_client", lambda token, api_url: client
        )
        return client

    return make


async def test_start_and_run_collect_output(install):
    client = install(
        create_command=(200, {"pid": 42}),
        stream=FakeStreamResponse(
            200,
            [
                line({"started": {"pid": 42}}),
                line({"stdout": b64("Hel")}),
                line({"keepalive": {}}),
                line({"stdout": b64("lo\n")}) + line({"stderr": b64("warn\n")}),
                line({"exit": {"exit_code": 3, "status": "exited"}}),
            ],
        ),
    )
    sb = await Sandbox.get(ID)
    out = []
    result = await sb.commands.run('echo "Hello"', cwd="/w", on_stdout=out.append)
    assert (result.pid, result.exit_code, result.stdout, result.stderr) == (
        42,
        3,
        "Hello\n",
        "warn\n",
    )
    assert out == ["Hel", "lo\n"]
    name, args = client.sandboxes.calls[-1]
    assert name == "create_command"
    assert args == (ID, {"cmd": "bash", "args": ["-lc", 'echo "Hello"'], "cwd": "/w"})
    assert client._client._pipeline and client.requested == [
        ("https://sandbox.test/v2/sandboxes/sb-1/commands/42/stream", True)
    ]
    assert client.stream.closed


async def test_stream_events_and_split_multibyte_text(install):
    data = "héllo".encode("utf-8")
    install(
        stream=FakeStreamResponse(
            200,
            [
                line({"stdout": b64(data[:2])}) + line({"stdout": b64(data[2:])}),
                line({"exit": {"exit_code": 0}}),
            ],
        )
    )
    sb = await Sandbox.get(ID)
    cmd = sb.commands.connect(42)
    assert [e.type async for e in cmd.stream()] == ["stdout", "stdout", "exit"]
    chunks = []
    install(
        stream=FakeStreamResponse(
            200,
            [
                line({"stdout": b64(data[:2])}),
                line({"stdout": b64(data[2:])}),
                line({"exit": {"exit_code": 0}}),
            ],
        )
    )
    sb = await Sandbox.get(ID)
    result = await sb.commands.connect(42).wait(on_stdout=chunks.append)
    assert result.stdout == "héllo" and all("�" not in c for c in chunks)


async def test_stream_failures(install):
    install(stream=FakeStreamResponse(200, [line({"stdout": b64("partial")})]))
    sb = await Sandbox.get(ID)
    with pytest.raises(SandboxError, match="ended before the command exited"):
        await sb.commands.connect(42).wait()

    install(
        stream=FakeStreamResponse(
            200,
            [
                line({"started": {"pid": 42}})
                + json.dumps({"error": {"http_code": 500, "message": "gateway failed"}})
            ],
        )
    )
    sb = await Sandbox.get(ID)
    with pytest.raises(SandboxError, match="gateway failed"):
        await sb.commands.connect(42).wait()


async def test_unknown_pid_is_not_found_and_says_why(install):
    install(
        stream=FakeStreamResponse(
            404, body={"id": "not_found", "message": "not found", "request_id": "r"}
        )
    )
    sb = await Sandbox.get(ID)
    with pytest.raises(NotFoundError, match="already exited") as info:
        await sb.commands.connect(99).wait()
    assert info.value.request_id == "r"


async def test_list_kill_stdin_and_validation(install):
    client = install(
        list_commands=(
            200,
            {"commands": [{"pid": 42, "cmd": "bash", "cwd": "/workspace"}]},
        ),
        post_commands_signal=(200, {}),
        post_commands_stdin=(200, {}),
        create_command=(200, {}),
    )
    sb = await Sandbox.get(ID)
    assert [(c.pid, c.cmd, c.cwd) for c in await sb.commands.list()] == [
        (42, "bash", "/workspace")
    ]

    cmd = sb.commands.connect(42)
    await cmd.kill()
    await cmd.kill("SIGKILL")
    await cmd.write_stdin("hello\n", eof=True)
    await cmd.close_stdin()
    calls = [c for c in client.sandboxes.calls if c[0] != "get"]
    assert calls[1:] == [
        (
            "post_commands_signal",
            (ID, 42, {"signal": "SANDBOX_COMMAND_SIGNAL_SIGTERM"}),
        ),
        (
            "post_commands_signal",
            (ID, 42, {"signal": "SANDBOX_COMMAND_SIGNAL_SIGKILL"}),
        ),
        ("post_commands_stdin", (ID, 42, {"data": b64("hello\n"), "eof": True})),
        ("post_commands_stdin", (ID, 42, {"eof": True})),
    ]
    with pytest.raises(SandboxError, match="unsupported signal"):
        await cmd.kill("SIGHUP")
    with pytest.raises(SandboxError, match="cmd"):
        await sb.commands.start(" ")
    with pytest.raises(SandboxError, match="pid"):
        await sb.commands.start("ls")
