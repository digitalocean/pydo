# pylint: disable=missing-function-docstring,redefined-outer-name,protected-access,duplicate-code,import-outside-toplevel,invalid-name,missing-class-docstring,too-few-public-methods,unused-argument
"""Mocked tests for async sandbox exec (``pydo.aio.sandbox``).

Fakes the generated operations (honouring ``cls``) and the client's pipeline, so
the async facade's own logic is covered without a network.
"""

import base64
import json
from types import SimpleNamespace

import pytest

from pydo.aio.sandbox import CommandError, InvalidRequestError, Sandbox, SandboxError
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
            if callable(body):
                body = body(*args)
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
        self.bodies = []

        async def run(request, stream=False):
            self.requested.append((request.url, stream))
            self.bodies.append(json.loads(request.content) if request.content else None)
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


EXEC_URL = ("https://sandbox.test/v2/sandboxes/sb-1/exec", True)


async def test_run_streams_and_collects_output(install):
    client = install(
        stream=FakeStreamResponse(
            200,
            [
                line({"stderr": b64("oops\n")}),
                line({"stdout": b64("Hel")}),
                line({"keepalive": {}}),
                line({"stdout": b64("lo\n")}) + line({"exit": {"exit_code": 3}}),
            ],
        ),
    )
    sb = await Sandbox.get(ID)
    out = []
    result = await sb.exec.run(
        "echo hello", cwd="/w", timeout_seconds=9, on_stdout=out.append
    )
    assert (result.exit_code, result.stdout, result.stderr) == (3, "Hello\n", "oops\n")
    assert out == ["Hel", "lo\n"]
    assert client.requested == [EXEC_URL]
    assert client.bodies == [
        {"argv": ["bash", "-lc", "echo hello"], "workdir": "/w", "timeout_seconds": "9"}
    ]
    assert client.stream.closed


async def test_exit_code_omitted_is_zero_and_envelopes_split_across_chunks(install):
    text = line({"stdout": b64("hé".encode())}) + line({"exit": {"duration_ms": "7"}})
    raw = text.replace("\n", "").encode()
    install(
        stream=FakeStreamResponse(200, [raw[i : i + 7] for i in range(0, len(raw), 7)])
    )
    sb = await Sandbox.get(ID)
    result = await sb.exec.run(["x"], stdin=b"in")
    assert (result.exit_code, result.stdout, result.duration_ms) == (0, "hé", 7)


async def test_stream_failures(install):
    install(stream=FakeStreamResponse(200, [line({"stdout": b64("partial")})]))
    sb = await Sandbox.get(ID)
    with pytest.raises(SandboxError, match="ended before the process exited"):
        await sb.exec.run("x")
    install(
        stream=FakeStreamResponse(
            200, [json.dumps({"error": {"http_code": 500, "message": "boom"}})]
        )
    )
    sb = await Sandbox.get(ID)
    with pytest.raises(SandboxError, match="boom"):
        await sb.exec.run("x")


async def test_a_400_before_the_stream_is_a_typed_error(install):
    client = install(
        stream=FakeStreamResponse(
            400, body={"id": "bad_request", "message": "no PTY on this template"}
        )
    )
    sb = await Sandbox.get(ID)
    with pytest.raises(InvalidRequestError, match="no PTY") as info:
        await sb.exec.start(pty=True)
    assert info.value.code == "bad_request"
    assert client.stream.closed


async def test_start_exposes_the_id_iterates_and_tracks_the_stdin_offset(install):
    offsets = iter(["3", "3"])
    client = install(
        post_exec_stdin=(200, lambda *a: {"offset": next(offsets)}),
        post_exec_resize=(200, {}),
        stream=FakeStreamResponse(
            200,
            [
                line({"started": {"exec_id": "ex-1"}}),
                line({"stdout": b64("hi\n")}) + line({"exit": {}}),
            ],
        ),
    )
    sb = await Sandbox.get(ID)
    async with await sb.exec.start(["cat"], pty={"rows": 24}) as session:
        assert session.exec_id == "ex-1"
        assert client.bodies == [
            {"argv": ["cat"], "keep_stdin_open": True, "pty": {"rows": 24}}
        ]
        await session.write_stdin("hi\n")
        await session.write_stdin(None, eof=True)
        await session.resize(30, 90)
        with pytest.raises(SandboxError, match="1 to 1000"):
            await session.resize(0, 90)
        assert [e.type async for e in session] == ["started", "stdout", "exit"]
    calls = [c for c in client.sandboxes.calls if c[0].startswith("post_exec")]
    assert calls == [
        ("post_exec_stdin", (ID, "ex-1", {"offset": "0", "data": b64("hi\n")})),
        ("post_exec_stdin", (ID, "ex-1", {"offset": "3", "eof": True})),
        ("post_exec_resize", (ID, "ex-1", {"rows": 30, "cols": 90})),
    ]
    assert client.stream.closed


async def test_plain_start_has_no_id_and_validation(install):
    client = install(stream=FakeStreamResponse(200, [line({"exit": {}})]))
    sb = await Sandbox.get(ID)
    session = await sb.exec.start("true", keep_stdin_open=False)
    assert session.exec_id is None
    with pytest.raises(SandboxError, match="no ID"):
        await session.write_stdin("x")
    assert (await session.wait()).exit_code == 0
    for call in (lambda: sb.exec.run([]), lambda: sb.exec.run("x", timeout_seconds=-1)):
        with pytest.raises(SandboxError):
            await call()
    assert len(client.requested) == 1


async def test_exports():
    import pydo.aio.sandbox as mod

    for name in ("Exec", "ExecSession", "ExecResult", "ExecEvent"):
        assert name in mod.__all__


def _exit_stream(code):
    return FakeStreamResponse(
        200, [line({"stdout": b64("out\n")}) + line({"exit": {"exit_code": code}})]
    )


async def test_exec_is_callable_and_reports_ok(install):
    client = install(stream=_exit_stream(0))
    sb = await Sandbox.get(ID)
    result = await sb.exec("echo out")
    assert (result.exit_code, result.stdout, result.ok) == (0, "out\n", True)
    assert client.bodies == [{"argv": ["bash", "-lc", "echo out"]}]


async def test_exec_call_maps_env_and_a_duration_timeout(install):
    client = install(stream=_exit_stream(0))
    sb = await Sandbox.get(ID)
    await sb.exec("pytest -x", cwd="/workspace", env={"CI": "1"}, timeout="2m")
    assert client.bodies == [
        {
            "argv": ["bash", "-lc", "pytest -x"],
            "workdir": "/workspace",
            "env_vars": {"CI": "1"},
            "timeout_seconds": "120",
        }
    ]


async def test_exec_call_does_not_raise_on_failure_unless_checked(install):
    install(stream=_exit_stream(3))
    sb = await Sandbox.get(ID)
    result = await sb.exec("exit 3")
    assert (result.exit_code, result.ok) == (3, False)
    with pytest.raises(CommandError) as info:
        await sb.exec("exit 3", check=True)
    assert isinstance(info.value, SandboxError)
    assert str(info.value) == "command exited with code 3"
    assert info.value.result.exit_code == 3 and info.value.result.stdout == "out\n"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"timeout": "soon"},
        {"timeout": "1d"},
        {"timeout": -1},
        {"timeout": "-5"},
        {"timeout": 1.5},
        {"env": {"A": "1"}, "env_vars": {"B": "2"}},
        {"timeout": 5, "timeout_seconds": 5},
    ],
)
async def test_exec_call_validates_options_before_any_request(install, kwargs):
    client = install(stream=_exit_stream(0))
    sb = await Sandbox.get(ID)
    with pytest.raises(SandboxError):
        await sb.exec("true", **kwargs)
    assert client.requested == []


async def test_run_and_start_still_work_beside_the_call(install):
    client = install(stream=_exit_stream(0))
    sb = await Sandbox.get(ID)
    assert (await sb.exec.run(["true"])).ok
    assert client.bodies == [{"argv": ["true"]}]
    session = await sb.exec.start(["true"], keep_stdin_open=False)
    assert (await session.wait()).ok
