# pylint: disable=missing-function-docstring,redefined-outer-name
"""Mocked tests for the E2B compat client (``pydo.sandbox.compat.e2b``).

Runs through the real sync pipeline with ``responses``.
"""

import base64
import json

import pytest
import responses

from pydo.sandbox import SandboxError, SandboxNotImplementedError
from pydo.sandbox.compat import e2b

API = "https://sandbox.test"
ID = "sb-1"
RAW = {
    "sandbox_id": ID,
    "template": "coding-base",
    "state": "SANDBOX_STATE_RUNNING",
    "size_slug": "mars-2vcpu-4gb",
    "created_at": "2026-11-20T12:00:00Z",
}
PAUSED = dict(RAW, state="SANDBOX_STATE_PAUSED")


def b64(text):
    return base64.b64encode(text.encode()).decode()


def event(**result):
    return json.dumps({"result": result}) + "\n"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("DIGITALOCEAN_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("DIGITALOCEAN_API_URL", raising=False)


@pytest.fixture
def rsps():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        yield mock


@pytest.fixture
def client():
    return e2b.E2bClient(api_key="test-token", do_api_url=API)


def last_body(rsps):
    return json.loads(rsps.calls[-1].request.body)


def sandbox_of(client, rsps):
    rsps.add(responses.POST, API + "/v2/sandboxes", json={"sandbox": RAW}, status=201)
    return client.Sandbox.create()


def test_create_sends_the_digitalocean_defaults_and_maps_options(client, rsps):
    rsps.add(responses.POST, API + "/v2/sandboxes", json={"sandbox": RAW}, status=201)
    sandbox = client.Sandbox.create(
        template="coding-base", envs={"A": "1"}, allow_internet_access=False
    )
    assert sandbox.sandbox_id == ID
    assert last_body(rsps) == {
        "template": "coding-base",
        "size_slug": "mars-2vcpu-4gb",
        "allow_internet_access": False,
        "env_vars": {"A": "1"},
    }
    assert rsps.calls[-1].request.headers["Authorization"] == "Bearer test-token"


def test_api_key_per_call_is_the_digitalocean_token(rsps):
    rsps.add(responses.POST, API + "/v2/sandboxes", json={"sandbox": RAW}, status=201)
    cls = e2b.E2bClient(do_api_url=API).Sandbox
    cls.create(api_key="per-call")
    assert rsps.calls[-1].request.headers["Authorization"] == "Bearer per-call"


def test_client_size_is_a_digitalocean_extra(rsps):
    rsps.add(responses.POST, API + "/v2/sandboxes", json={"sandbox": RAW}, status=201)
    e2b.E2bClient(api_key="t", do_api_url=API, size="mars-4vcpu-8gb").Sandbox.create()
    assert last_body(rsps)["size_slug"] == "mars-4vcpu-8gb"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"timeout": 60},
        {"metadata": {"a": "b"}},
        {"mcp": {"x": {}}},
        {"network": {"deny_out": ["0.0.0.0/0"]}},
        {"volume_mounts": {"/data": "v"}},
        {"idempotency_key": "k"},
        {"cpu_count": 2},
        {"secure": False},
        {"domain": "e2b.app"},
        {"api_url": "https://api.e2b.app"},
    ],
)
def test_create_refuses_options_it_cannot_honor_before_any_request(
    client, rsps, kwargs
):
    with pytest.raises(SandboxNotImplementedError) as err:
        client.Sandbox.create(**kwargs)
    assert "E2B.Sandbox.create" in str(err.value)
    assert not rsps.calls


def test_client_side_options_are_accepted_and_ignored(client, rsps):
    rsps.add(responses.POST, API + "/v2/sandboxes", json={"sandbox": RAW}, status=201)
    client.Sandbox.create(request_timeout=5, debug=False, retries=1, headers={"a": "b"})
    assert len(rsps.calls) == 1


def test_run_returns_the_result_and_calls_callbacks(client, rsps):
    sandbox = sandbox_of(client, rsps)
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands" % ID, json={"pid": 7})
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/7/stream" % ID,
        body=event(started={"pid": 7})
        + event(stdout=b64("hello\n"))
        + event(stderr=b64("warn\n"))
        + event(exit={"exit_code": 0, "status": "EXITED"}),
    )
    seen = []
    result = sandbox.commands.run(
        "echo hello", cwd="/w", envs={"K": "v"}, on_stdout=seen.append
    )
    assert (result.stdout, result.stderr, result.exit_code) == ("hello\n", "warn\n", 0)
    assert seen == ["hello\n"]
    body = json.loads(rsps.calls[-2].request.body)
    assert body["cmd"] == "bash" and body["args"] == ["-lc", "echo hello"]
    assert body["cwd"] == "/w" and body["env_vars"] == {"K": "v"}


def test_run_raises_command_exit_exception_on_a_non_zero_exit_like_e2b(client, rsps):
    sandbox = sandbox_of(client, rsps)
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands" % ID, json={"pid": 8})
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/8/stream" % ID,
        body=event(stderr=b64("boom"))
        + event(exit={"exit_code": 3, "status": "EXITED"}),
    )
    with pytest.raises(e2b.CommandExitException) as err:
        sandbox.commands.run("false")
    assert err.value.exit_code == 3 and err.value.stderr == "boom"
    assert isinstance(err.value, e2b.SandboxException)


def test_run_background_returns_a_handle_that_waits(client, rsps):
    sandbox = sandbox_of(client, rsps)
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands" % ID, json={"pid": 9})
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/9/stream" % ID,
        body=event(stdout=b64("done")) + event(exit={"exit_code": 0}),
    )
    handle = sandbox.commands.run("sleep 1", background=True)
    assert handle.pid == 9
    assert handle.wait().stdout == "done"


def test_run_with_stdin_and_shell_starts_the_given_executable(client, rsps):
    sandbox = sandbox_of(client, rsps)
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands" % ID, json={"pid": 5})
    handle = sandbox.commands.run(
        "cat", background=True, stdin=True, shell=["sh", "-c"]
    )
    assert last_body(rsps)["cmd"] == "sh"
    assert last_body(rsps)["args"] == ["-c", "cat"]
    assert last_body(rsps)["stdin"] is True
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands/5/stdin" % ID, json={})
    handle.send_stdin("hi")
    handle.close_stdin()
    assert len(rsps.calls) >= 4


def test_run_refuses_another_user(client, rsps):
    sandbox = sandbox_of(client, rsps)
    with pytest.raises(SandboxNotImplementedError, match="user"):
        sandbox.commands.run("id", user="root")


def test_commands_list_and_kill(client, rsps):
    sandbox = sandbox_of(client, rsps)
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands" % ID,
        json={"commands": [{"pid": 4, "cmd": "bash", "cwd": "/w"}]},
    )
    infos = sandbox.commands.list()
    assert [(i.pid, i.cmd, i.cwd) for i in infos] == [(4, "bash", "/w")]
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands/4/signal" % ID, json={})
    assert sandbox.commands.kill(4) is True
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes/%s/commands/99/signal" % ID,
        json={"id": "not_found", "message": "gone"},
        status=404,
    )
    assert sandbox.commands.kill(99) is False


def test_pause_and_connect_resume(client, rsps):
    sandbox = sandbox_of(client, rsps)
    rsps.add(
        responses.POST, API + "/v2/sandboxes/%s/pause" % ID, json={"sandbox": PAUSED}
    )
    assert sandbox.pause() is True
    rsps.add(responses.GET, API + "/v2/sandboxes/%s" % ID, json={"sandbox": PAUSED})
    rsps.add(
        responses.POST, API + "/v2/sandboxes/%s/resume" % ID, json={"sandbox": RAW}
    )
    again = client.Sandbox.connect(ID)
    assert again.sandbox_id == ID
    assert rsps.calls[-1].request.url.endswith("/resume")


def test_pause_by_id_and_kill_by_id(client, rsps):
    rsps.add(
        responses.POST, API + "/v2/sandboxes/%s/pause" % ID, json={"sandbox": PAUSED}
    )
    assert client.Sandbox.pause(ID) is True
    rsps.add(responses.DELETE, API + "/v2/sandboxes/%s" % ID, json={})
    assert client.Sandbox.kill(ID) is True


@pytest.mark.parametrize("kwargs", [{"keep_memory": False}, {"mode": "full"}])
def test_pause_refuses_semantic_options(client, rsps, kwargs):
    sandbox = sandbox_of(client, rsps)
    with pytest.raises(SandboxNotImplementedError):
        sandbox.pause(**kwargs)


def test_get_info_maps_what_the_api_returns(client, rsps):
    sandbox = sandbox_of(client, rsps)
    rsps.add(responses.GET, API + "/v2/sandboxes/%s" % ID, json={"sandbox": RAW})
    info = sandbox.get_info()
    assert info.sandbox_id == ID and info.template_id == "coding-base"
    assert info.state == e2b.SandboxState.RUNNING and info.metadata == {}
    assert info.end_at is None


def test_list_pages_and_state_filter(client, rsps):
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes",
        json={"sandboxes": [RAW], "next_page_token": "t2"},
    )
    paginator = client.Sandbox.list(
        query=e2b.SandboxQuery(state=[e2b.SandboxState.RUNNING]), limit=1
    )
    assert paginator.has_next
    items = paginator.next_items()
    assert [i.sandbox_id for i in items] == [ID]
    assert paginator.has_next and paginator.next_token == "t2"
    assert "state=SANDBOX_STATE_RUNNING" in rsps.calls[-1].request.url


@pytest.mark.parametrize(
    "kwargs",
    [
        {"order": "asc"},
        {"query": e2b.SandboxQuery(metadata={"a": "b"})},
        {"query": e2b.SandboxQuery(template="x")},
    ],
)
def test_list_refuses_filters_the_api_lacks(client, rsps, kwargs):
    with pytest.raises(SandboxNotImplementedError):
        client.Sandbox.list(**kwargs)


def test_snapshots_create_waits_and_lists(client, rsps):
    sandbox = sandbox_of(client, rsps)
    snap = {
        "snapshot_id": "sn-1",
        "sandbox_id": ID,
        "name": "mine",
        "state": "SNAPSHOT_STATE_CREATING",
        "created_at": "2026-11-20T12:00:00Z",
    }
    done = dict(snap, state="SNAPSHOT_STATE_COMPLETE")
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes/%s/snapshots" % ID,
        json={"snapshot": snap},
        status=202,
    )
    rsps.add(
        responses.GET, API + "/v2/sandboxes/snapshots/sn-1", json={"snapshot": done}
    )
    info = sandbox.create_snapshot(name="mine")
    assert info.snapshot_id == "sn-1" and info.names == ["mine"]
    rsps.add(responses.GET, API + "/v2/sandboxes/snapshots", json={"snapshots": [done]})
    pages = sandbox.list_snapshots()
    assert [s.snapshot_id for s in pages.next_items()] == ["sn-1"]
    assert "sandbox_id=%s" % ID in rsps.calls[-1].request.url
    rsps.add(responses.DELETE, API + "/v2/sandboxes/snapshots/sn-1", json={})
    assert client.Sandbox.delete_snapshot("sn-1") is True


def test_api_errors_become_e2b_exceptions(client, rsps):
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/missing",
        json={"id": "not_found", "message": "no such sandbox"},
        status=404,
    )
    with pytest.raises(e2b.NotFoundException) as err:
        client.Sandbox.connect("missing")
    assert isinstance(err.value, e2b.SandboxNotFoundException)
    assert err.value.status_code == 404
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes",
        json={"id": "unauthorized", "message": "no"},
        status=401,
    )
    with pytest.raises(e2b.AuthenticationException):
        client.Sandbox.create()


def test_direct_construction_is_refused():
    with pytest.raises(SandboxError, match="Sandbox.create"):
        e2b.Sandbox()


def test_client_refuses_e2b_urls_and_unknown_options():
    with pytest.raises(SandboxNotImplementedError):
        e2b.E2bClient(api_key="x", domain="e2b.app")
    with pytest.raises(TypeError):
        e2b.E2bClient(api_key="x", frobnicate=True)
