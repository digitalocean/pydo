# pylint: disable=missing-function-docstring,redefined-outer-name,consider-using-f-string,duplicate-code,invalid-name,use-implicit-booleaness-not-comparison
"""Mocked tests for sandbox commands (``pydo.sandbox``), through the real pipeline."""

import base64
import json

import pytest
import responses

from pydo.sandbox import NotFoundError, Sandbox, SandboxError
from pydo.sandbox._commands import JsonObjectReader

API = "https://sandbox.test"
CONN = {"token": "test-token", "api_url": API}
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


def stream_body(*events):
    return "".join(events)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("DIGITALOCEAN_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("DIGITALOCEAN_API_URL", raising=False)


@pytest.fixture
def sandbox():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(responses.GET, API + "/v2/sandboxes/" + ID, json={"sandbox": RAW})
        sb = Sandbox.get(ID, **CONN)
        yield sb, rsps


def body_of(rsps, index=-1):
    return json.loads(rsps.calls[index].request.body)


def test_start_sends_the_executable_and_returns_a_handle(sandbox):
    sb, rsps = sandbox
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands" % ID, json={"pid": 42})
    cmd = sb.commands.start(
        "sleep",
        args=["60"],
        cwd="/workspace",
        env_vars={"A": "1"},
        stdin=True,
        timeout_seconds=30,
    )
    assert cmd.pid == 42
    assert body_of(rsps) == {
        "cmd": "sleep",
        "args": ["60"],
        "cwd": "/workspace",
        "env_vars": {"A": "1"},
        "stdin": True,
        "timeout_seconds": "30",
    }


def test_start_validates_before_sending(sandbox):
    sb, _ = sandbox
    with pytest.raises(SandboxError, match="cmd"):
        sb.commands.start(" ")


def test_list_returns_the_running_commands(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands" % ID,
        json={
            "commands": [
                {"pid": 42, "cmd": "bash", "cwd": "/workspace"},
                {"pid": 43, "cmd": "sleep"},
            ]
        },
    )
    listed = sb.commands.list()
    assert [(c.pid, c.cmd, c.cwd) for c in listed] == [
        (42, "bash", "/workspace"),
        (43, "sleep", None),
    ]


def test_run_starts_bash_and_collects_output(sandbox):
    sb, rsps = sandbox
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands" % ID, json={"pid": 42})
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/42/stream" % ID,
        body=stream_body(
            line({"started": {"pid": 42}}),
            line({"stdout": b64("Hel")}),
            line({"keepalive": {}}),
            line({"stdout": b64("lo\n")}),
            line({"stderr": b64("warn\n")}),
            line({"exit": {"exit_code": 3, "status": "exited"}}),
        ),
    )
    out, err = [], []
    result = sb.commands.run(
        'echo "Hello"', cwd="/w", on_stdout=out.append, on_stderr=err.append
    )
    assert (
        result.pid,
        result.exit_code,
        result.stdout,
        result.stderr,
        result.status,
    ) == (
        42,
        3,
        "Hello\n",
        "warn\n",
        "exited",
    )
    assert out == ["Hel", "lo\n"] and err == ["warn\n"]
    assert body_of(rsps, 1) == {
        "cmd": "bash",
        "args": ["-lc", 'echo "Hello"'],
        "cwd": "/w",
    }
    stream_call = rsps.calls[2].request
    assert stream_call.headers["Authorization"] == "Bearer test-token"


def test_multibyte_text_split_across_chunks_stays_whole(sandbox):
    sb, rsps = sandbox
    data = "héllo".encode("utf-8")
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/42/stream" % ID,
        body=stream_body(
            line({"stdout": b64(data[:2])}),
            line({"stdout": b64(data[2:])}),
            line({"exit": {"exit_code": 0}}),
        ),
    )
    chunks = []
    result = sb.commands.connect(42).wait(on_stdout=chunks.append)
    assert result.stdout == "héllo"
    assert all("�" not in c for c in chunks)


def test_stream_yields_typed_events_and_drops_keepalives(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/42/stream" % ID,
        body=stream_body(
            line({"started": {"pid": 42}}),
            line({"keepalive": {}}),
            line({"stdout": b64("a")}),
            line({"exit": {"exit_code": 0, "status": "exited"}}),
        ),
    )
    assert [e.type for e in sb.commands.connect(42).stream()] == [
        "started",
        "stdout",
        "exit",
    ]


def test_a_stream_that_ends_before_exit_is_an_error(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/42/stream" % ID,
        body=line({"stdout": b64("partial")}),
    )
    with pytest.raises(SandboxError, match="ended before the command exited"):
        sb.commands.connect(42).wait()


def test_an_exit_with_an_error_is_returned_in_the_result(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/42/stream" % ID,
        body=line(
            {"exit": {"exit_code": 137, "status": "killed", "error": "out of memory"}}
        ),
    )
    result = sb.commands.connect(42).wait()
    assert (result.exit_code, result.error) == (137, "out of memory")


def test_an_unknown_pid_is_not_found_and_says_why(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/99/stream" % ID,
        json={"id": "not_found", "message": "not found", "request_id": "r"},
        status=404,
    )
    with pytest.raises(NotFoundError, match="already exited") as info:
        sb.commands.connect(99).wait()
    assert info.value.status == 404 and info.value.request_id == "r"


def test_a_stream_error_envelope_is_raised(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/42/stream" % ID,
        body=line({"started": {"pid": 42}})
        + json.dumps({"error": {"http_code": 500, "message": "gateway failed"}})
        + "\n",
    )
    with pytest.raises(SandboxError, match="gateway failed") as info:
        sb.commands.connect(42).wait()
    assert info.value.status == 500


def test_write_stdin_sends_base64_and_eof(sandbox):
    sb, rsps = sandbox
    url = API + "/v2/sandboxes/%s/commands/42/stdin" % ID
    rsps.add(responses.POST, url, json={})
    cmd = sb.commands.connect(42)
    cmd.write_stdin("hello\n", eof=True)
    assert body_of(rsps) == {"data": b64("hello\n"), "eof": True}
    cmd.write_stdin(b"raw")
    assert body_of(rsps) == {"data": b64("raw")}
    cmd.close_stdin()
    assert body_of(rsps) == {"eof": True}


def test_kill_sends_sigterm_by_default_and_sigkill_on_request(sandbox):
    sb, rsps = sandbox
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands/42/signal" % ID, json={})
    cmd = sb.commands.connect(42)
    cmd.kill()
    assert body_of(rsps) == {"signal": "SANDBOX_COMMAND_SIGNAL_SIGTERM"}
    cmd.kill("SIGKILL")
    assert body_of(rsps) == {"signal": "SANDBOX_COMMAND_SIGNAL_SIGKILL"}
    with pytest.raises(SandboxError, match="unsupported signal"):
        cmd.kill("SIGHUP")


def test_an_html_reply_is_a_typed_error_with_the_status(sandbox):
    sb, rsps = sandbox
    url = API + "/v2/sandboxes/%s/commands" % ID
    rsps.add(
        responses.POST,
        url,
        body="<html><body><h1>404 page not found</h1></body></html>",
        status=404,
        content_type="text/html",
    )
    with pytest.raises(
        NotFoundError,
        match=r"unexpected text/html response \(HTTP 404\).*404 page not found",
    ) as info:
        sb.commands.run("echo hi")
    assert info.value.status == 404
    rsps.replace(
        responses.POST, url, body="bad gateway", status=502, content_type="text/plain"
    )
    with pytest.raises(SandboxError, match="HTTP 502") as info:
        sb.commands.start("ls")
    assert info.value.status == 502


def test_api_errors_on_start_and_list_are_typed(sandbox):
    sb, rsps = sandbox
    url = API + "/v2/sandboxes/%s/commands" % ID
    rsps.add(
        responses.POST,
        url,
        json={"id": "not_found", "message": "Sandbox not found."},
        status=404,
    )
    with pytest.raises(NotFoundError):
        sb.commands.start("ls")
    rsps.add(responses.GET, url, json={"id": "forbidden", "message": "no"}, status=403)
    with pytest.raises(SandboxError) as info:
        sb.commands.list()
    assert info.value.status == 403


def test_json_object_reader():
    reader = JsonObjectReader()
    assert reader.push('{"a":1}\n{"b":2}{"c":3}\n') == [{"a": 1}, {"b": 2}, {"c": 3}]
    assert reader.push('{"a":{"x":') == []
    assert reader.push('1}}\n{"b"') == [{"a": {"x": 1}}]
    assert reader.push(":2}") == [{"b": 2}]
    assert reader.push('{"s":"} { \\" }"}{"t":"x"}') == [{"s": '} { " }'}, {"t": "x"}]
