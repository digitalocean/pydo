# pylint: disable=missing-function-docstring,redefined-outer-name
"""Mocked tests for sandbox exec (``pydo.sandbox``), through the real pipeline."""

import base64
import json
import threading

import pytest
import responses

from pydo.sandbox import CommandError, InvalidRequestError, Sandbox, SandboxError
from pydo.sandbox._exec import JsonObjectReader, parse_duration

API = "https://sandbox.test"
CONN = {"token": "test-token", "api_url": API}
ID = "sb-1"
EXEC = API + "/v2/sandboxes/%s/exec" % ID
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


def test_run_collects_output_and_returns_a_non_zero_exit(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.POST,
        EXEC,
        content_type="application/json",
        body=line({"stderr": b64("oops\n")})
        + line({"stdout": b64("hello\n")})
        + line({"exit": {"exit_code": 3, "duration_ms": "39", "status": "exited"}}),
    )
    out, err = [], []
    result = sb.exec.run(
        "echo hello; echo oops >&2; exit 3", on_stdout=out.append, on_stderr=err.append
    )
    assert (result.exit_code, result.stdout, result.stderr) == (3, "hello\n", "oops\n")
    assert (result.duration_ms, result.status, result.error) == (39, "exited", None)
    assert out == ["hello\n"] and err == ["oops\n"]
    assert body_of(rsps) == {
        "argv": ["bash", "-lc", "echo hello; echo oops >&2; exit 3"]
    }
    assert rsps.calls[-1].request.headers["Authorization"] == "Bearer test-token"


def test_an_omitted_exit_code_is_zero(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.POST,
        EXEC,
        body=line({"stdout": b64("hi\n")}) + line({"exit": {"duration_ms": "3892"}}),
    )
    result = sb.exec.run(["cat"])
    assert (result.exit_code, result.duration_ms, result.stdout) == (0, 3892, "hi\n")


def test_argv_list_is_sent_as_is_and_options_map_to_the_body(sandbox):
    sb, rsps = sandbox
    rsps.add(responses.POST, EXEC, body=line({"exit": {}}))
    sb.exec.run(
        ["python", "-c", "print(1)"],
        cwd="/workspace",
        env_vars={"A": "1"},
        timeout_seconds=30,
        stdin="in\n",
    )
    assert body_of(rsps) == {
        "argv": ["python", "-c", "print(1)"],
        "workdir": "/workspace",
        "env_vars": {"A": "1"},
        "timeout_seconds": "30",
        "stdin": b64("in\n"),
    }


def test_stdin_bytes_are_base64_in_the_first_frame(sandbox):
    sb, rsps = sandbox
    rsps.add(responses.POST, EXEC, body=line({"exit": {}}))
    sb.exec.run("cat", stdin=b"\x00\xff")
    assert body_of(rsps)["stdin"] == b64(b"\x00\xff")


def test_keepalives_are_dropped_and_multibyte_text_stays_whole(sandbox):
    sb, rsps = sandbox
    data = "héllo".encode("utf-8")
    rsps.add(
        responses.POST,
        EXEC,
        body=line({"stdout": b64(data[:2])})
        + line({"keepalive": {}})
        + line({"stdout": b64(data[2:])})
        + line({"exit": {}}),
    )
    chunks = []
    result = sb.exec.run("x", on_stdout=chunks.append)
    assert result.stdout == "héllo"
    assert all("�" not in c for c in chunks)
    rsps.replace(
        responses.POST,
        EXEC,
        body=line({"keepalive": {}}) + line({"stdout": b64("a")}) + line({"exit": {}}),
    )
    with sb.exec.start("x", keep_stdin_open=False) as session:
        assert [e.type for e in session.events()] == ["stdout", "exit"]


def test_envelope_split_across_chunks_and_without_newlines():
    reader = JsonObjectReader()
    text = line({"stdout": b64("a{b}")}) + line({"exit": {}})
    text = text.replace("\n", "")
    got = []
    for i in range(0, len(text), 5):
        got += reader.push(text[i : i + 5])
    assert got == [{"result": {"stdout": b64("a{b}")}}, {"result": {"exit": {}}}]


def test_an_error_envelope_raises(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.POST,
        EXEC,
        body=line({"stdout": b64("a")})
        + json.dumps({"error": {"http_code": 500, "message": "boom"}}),
    )
    with pytest.raises(SandboxError, match="boom") as info:
        sb.exec.run("x")
    assert info.value.status == 500


def test_a_stream_that_ends_before_exit_is_an_error(sandbox):
    sb, rsps = sandbox
    rsps.add(responses.POST, EXEC, body=line({"stdout": b64("partial")}))
    with pytest.raises(SandboxError, match="ended before the process exited"):
        sb.exec.run("x")


def test_a_400_before_the_stream_is_a_typed_error(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.POST,
        EXEC,
        status=400,
        json={
            "id": "bad_request",
            "message": "this sandbox's template image does not support interactive stdin or PTY exec",
        },
    )
    with pytest.raises(InvalidRequestError, match="does not support") as info:
        sb.exec.start("cat")
    assert (info.value.status, info.value.code) == (400, "bad_request")


def test_start_reads_started_and_exposes_the_exec_id(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.POST,
        EXEC,
        body=line({"started": {"exec_id": "ex-1"}})
        + line({"stdout": b64("hi\n")})
        + line({"exit": {"duration_ms": "5"}}),
    )
    session = sb.exec.start(["cat"])
    assert session.exec_id == "ex-1"
    assert body_of(rsps) == {"argv": ["cat"], "keep_stdin_open": True}
    events = list(session)
    assert [e.type for e in events] == ["started", "stdout", "exit"]
    assert events[0].exec_id == "ex-1" and events[1].text == "hi\n"
    assert events[2].duration_ms == 5


def test_start_wait_returns_the_result(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.POST,
        EXEC,
        body=line({"started": {"exec_id": "ex-1"}})
        + line({"stdout": b64("hi\n")})
        + line({"exit": {}}),
    )
    with sb.exec.start(["cat"]) as session:
        assert session.wait().stdout == "hi\n"


def test_plain_start_has_no_exec_id_and_refuses_stdin_and_resize(sandbox):
    sb, rsps = sandbox
    rsps.add(responses.POST, EXEC, body=line({"exit": {}}))
    session = sb.exec.start("true", keep_stdin_open=False)
    assert session.exec_id is None
    assert "keep_stdin_open" not in body_of(rsps)
    with pytest.raises(SandboxError, match="no ID"):
        session.write_stdin("x")
    with pytest.raises(SandboxError, match="no ID"):
        session.resize(10, 10)
    session.close()


def test_write_stdin_tracks_the_offset_and_eof(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.POST,
        EXEC,
        body=line({"started": {"exec_id": "ex-1"}}) + line({"exit": {}}),
    )
    stdin = API + "/v2/sandboxes/%s/exec/ex-1/stdin" % ID
    rsps.add(responses.POST, stdin, json={"offset": "3"})
    session = sb.exec.start(["cat"])
    session.write_stdin("hi\n")
    assert body_of(rsps) == {"offset": "0", "data": b64("hi\n")}
    rsps.replace(responses.POST, stdin, json={"offset": "5"})
    session.write_stdin(b"ab")
    assert body_of(rsps) == {"offset": "3", "data": b64("ab")}
    session.close_stdin()
    assert body_of(rsps) == {"offset": "5", "eof": True}
    session.close()


def test_concurrent_writes_are_serialized(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.POST,
        EXEC,
        body=line({"started": {"exec_id": "ex-1"}}) + line({"exit": {}}),
    )
    seen = []

    def callback(request):
        seen.append(json.loads(request.body)["offset"])
        return 200, {}, json.dumps({"offset": str(int(seen[-1]) + 1)})

    rsps.add_callback(
        responses.POST,
        API + "/v2/sandboxes/%s/exec/ex-1/stdin" % ID,
        callback=callback,
        content_type="application/json",
    )
    session = sb.exec.start(["cat"])
    threads = [threading.Thread(target=session.write_stdin, args=("x",)) for _ in "abc"]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(seen) == ["0", "1", "2"]
    session.close()


def test_pty_body_and_resize(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.POST,
        EXEC,
        body=line({"started": {"exec_id": "ex-1"}}) + line({"exit": {}}),
    )
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/exec/ex-1/resize" % ID, json={})
    session = sb.exec.start(pty={"rows": 24, "cols": 80, "term": "xterm"})
    assert body_of(rsps) == {
        "argv": [],
        "keep_stdin_open": True,
        "pty": {"rows": 24, "cols": 80, "term": "xterm"},
    }
    session.resize(40, 100)
    assert body_of(rsps) == {"rows": 40, "cols": 100}
    for rows, cols in [(0, 10), (10, 1001), ("a", 10), (True, 10)]:
        with pytest.raises(SandboxError, match="1 to 1000"):
            session.resize(rows, cols)
    assert len(rsps.calls) == 3
    session.close()


def test_pty_true_allows_a_command(sandbox):
    sb, rsps = sandbox
    rsps.add(
        responses.POST,
        EXEC,
        body=line({"started": {"exec_id": "ex-1"}}) + line({"exit": {}}),
    )
    sb.exec.start("top", pty=True, keep_stdin_open=False).close()
    assert body_of(rsps) == {"argv": ["bash", "-lc", "top"], "pty": {}}


def test_validation_happens_before_any_request(sandbox):
    sb, rsps = sandbox
    for call, match in [
        (lambda: sb.exec.run([]), "required"),
        (lambda: sb.exec.run(" "), "required"),
        (lambda: sb.exec.run(["a", 1]), "string"),
        (lambda: sb.exec.run("x", env_vars={"": "v"}), "env var"),
        (lambda: sb.exec.run("x", timeout_seconds=-1), "timeout_seconds"),
        (lambda: sb.exec.start("x", pty={"rows": 0}), "1 to 1000"),
        (lambda: sb.exec.start("x", pty={"bogus": 1}), "unknown pty"),
        (lambda: sb.exec.start([]), "required"),
    ]:
        with pytest.raises(SandboxError, match=match):
            call()
    with pytest.raises(TypeError):
        sb.exec.run("x", bogus=True)
    assert len(rsps.calls) == 1  # only the sandbox lookup


def test_the_namespace_is_exported():
    import pydo.sandbox as mod  # pylint: disable=import-outside-toplevel

    for name in ("Exec", "ExecSession", "ExecResult", "ExecEvent"):
        assert name in mod.__all__ and hasattr(mod, name)


def _exit(code):
    return line({"stdout": b64("out\n")}) + line({"exit": {"exit_code": code}})


def test_exec_is_callable_and_reports_ok(sandbox):
    sb, rsps = sandbox
    rsps.add(responses.POST, EXEC, body=_exit(0))
    result = sb.exec("echo out")
    assert (result.exit_code, result.stdout, result.ok) == (0, "out\n", True)
    assert body_of(rsps) == {"argv": ["bash", "-lc", "echo out"]}


def test_exec_call_maps_env_and_a_duration_timeout(sandbox):
    sb, rsps = sandbox
    rsps.add(responses.POST, EXEC, body=_exit(0))
    sb.exec("pytest -x", cwd="/workspace", env={"CI": "1"}, timeout="2m")
    assert body_of(rsps) == {
        "argv": ["bash", "-lc", "pytest -x"],
        "workdir": "/workspace",
        "env_vars": {"CI": "1"},
        "timeout_seconds": "120",
    }


def test_exec_call_does_not_raise_on_failure_unless_checked(sandbox):
    sb, rsps = sandbox
    rsps.add(responses.POST, EXEC, body=_exit(3))
    result = sb.exec("exit 3")
    assert (result.exit_code, result.ok) == (3, False)
    with pytest.raises(CommandError) as info:
        sb.exec("exit 3", check=True)
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
def test_exec_call_validates_options_before_any_request(sandbox, kwargs):
    sb, rsps = sandbox
    before = len(rsps.calls)
    with pytest.raises(SandboxError):
        sb.exec("true", **kwargs)
    assert len(rsps.calls) == before


def test_exec_duration_forms():
    assert [parse_duration(v) for v in (90, "90", "90s", "10m", "2h", " 5 m ")] == [
        90,
        90,
        90,
        600,
        7200,
        300,
    ]
    with pytest.raises(SandboxError, match="timeout"):
        parse_duration("x")


def test_run_and_start_still_work_beside_the_call(sandbox):
    sb, rsps = sandbox
    rsps.add(responses.POST, EXEC, body=_exit(0))
    assert sb.exec.run(["true"]).ok
    assert body_of(rsps) == {"argv": ["true"]}
    session = sb.exec.start(["true"], keep_stdin_open=False)
    assert session.wait().ok
