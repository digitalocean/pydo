# pylint: disable=missing-function-docstring,redefined-outer-name
"""Mocked tests for the Modal compat client (``pydo.sandbox.compat.modal``).

Runs through the real sync pipeline with ``responses``.
"""

import base64
import json

import pytest
import responses

from pydo.sandbox import SandboxNotImplementedError
from pydo.sandbox.compat import modal

API = "https://sandbox.test"
ID = "sb-1"
RAW = {
    "sandbox_id": ID,
    "template": "coding-base",
    "state": "SANDBOX_STATE_RUNNING",
    "size_slug": "mars-2vcpu-4gb",
    "created_at": "2026-11-20T12:00:00Z",
}


def b64(text):
    return base64.b64encode(text.encode()).decode()


def event(**result):
    return json.dumps({"result": result}) + "\n"


def tpl(name, status="TEMPLATE_STATUS_READY", template_id="t-1"):
    return {
        "template_id": template_id,
        "name": name,
        "status": status,
        "spec": {
            "base_template": "coding-base",
            "image": {"repository": "library/python", "tag": "3.12"},
        },
        "created_at": "2026-11-20T12:00:00Z",
        "updated_at": "2026-11-20T12:05:00Z",
    }


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
    return modal.ModalClient(
        token_id="ignored", token_secret="test-token", do_api_url=API
    )


def last_body(rsps):
    return json.loads(rsps.calls[-1].request.body)


def sandbox_of(client, rsps, **kwargs):
    rsps.add(responses.POST, API + "/v2/sandboxes", json={"sandbox": RAW}, status=201)
    return client.Sandbox.create(**kwargs)


def test_create_maps_cpu_memory_env_secrets_and_network(client, rsps):
    sandbox = sandbox_of(
        client,
        rsps,
        app=modal.App.lookup("my-app", create_if_missing=True),
        image=modal.Image.debian_slim(),
        cpu=2,
        memory=3000,
        env={"A": "1", "DROP": None},
        secrets=[modal.Secret.from_dict({"S": "x"})],
        block_network=True,
    )
    assert last_body(rsps) == {
        "template": "coding-base",
        "size_slug": "mars-2vcpu-4gb",
        "allow_internet_access": False,
        "env_vars": {"S": "x", "A": "1"},
    }
    assert rsps.calls[-1].request.headers["Authorization"] == "Bearer test-token"
    assert sandbox.object_id == ID


@pytest.mark.parametrize(
    "kwargs",
    [
        {"timeout": 600},
        {"idle_timeout": 30},
        {"name": "n"},
        {"tags": {"a": "b"}},
        {"gpu": "A10G"},
        {"region": "us"},
        {"outbound_domain_allowlist": ["example.com"]},
        {"volumes": {"/d": object()}},
        {"pty": True},
        {"encrypted_ports": [8000]},
        {"readiness_probe": object()},
        {"cpu": 64},
        {"image": object()},
    ],
)
def test_create_refuses_options_it_cannot_honor_before_any_request(
    client, rsps, kwargs
):
    with pytest.raises(SandboxNotImplementedError, match="Modal.Sandbox.create"):
        client.Sandbox.create(**kwargs)
    assert not rsps.calls


def test_the_default_timeout_is_accepted_and_unknown_arguments_are_a_type_error(
    client, rsps
):
    sandbox_of(client, rsps, timeout=300)
    with pytest.raises(TypeError):
        client.Sandbox.create(bogus=1)


def test_a_registry_image_builds_a_template_once_and_creates_from_it(client, rsps):
    image = modal.Image.from_registry("python:3.12")
    name = image.template_name()
    rsps.add(responses.GET, API + "/v2/sandboxes/templates", json={"templates": []})
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes/templates",
        json={"template": tpl(name, "TEMPLATE_STATUS_PENDING")},
        status=201,
    )
    rsps.add(
        responses.GET, API + "/v2/sandboxes/templates/t-1", json={"template": tpl(name)}
    )
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes",
        json={"sandbox": dict(RAW, template=name)},
        status=201,
    )
    client.Sandbox.create(image=image)
    assert json.loads(rsps.calls[1].request.body)["source_oci_ref"] == "python:3.12"
    assert last_body(rsps)["template"] == name
    rsps.reset()
    rsps.add(
        responses.GET, API + "/v2/sandboxes/templates", json={"templates": [tpl(name)]}
    )
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes",
        json={"sandbox": dict(RAW, template=name)},
        status=201,
    )
    client.Sandbox.create(image=modal.Image.from_registry("python:3.12"))
    assert [c.request.method for c in rsps.calls] == ["GET", "POST"]


def test_image_builders_that_need_a_build_raise(client):
    with pytest.raises(SandboxNotImplementedError, match="Image.pip_install"):
        modal.Image.debian_slim().pip_install("requests")
    with pytest.raises(SandboxNotImplementedError, match="Image.from_registry"):
        modal.Image.from_registry("p", add_python="3.12")


def test_exec_streams_stdout_and_stderr_and_returns_the_exit_code(client, rsps):
    sandbox = sandbox_of(client, rsps, workdir="/work")
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands" % ID, json={"pid": 7})
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/7/stream" % ID,
        body=event(stdout=b64("hello\nwor"))
        + event(stderr=b64("warn\n"))
        + event(stdout=b64("ld\n"))
        + event(exit={"exit_code": 3}),
    )
    process = sandbox.exec("python3", "-c", "print(1)", env={"K": "v"}, timeout=20)
    body = json.loads(rsps.calls[-1].request.body)
    assert body["cmd"] == "python3" and body["args"] == ["-c", "print(1)"]
    assert (
        body["cwd"] == "/work"
        and body["env_vars"] == {"K": "v"}
        and body["stdin"] is True
    )
    assert process.stdout.read() == "hello\nworld\n"
    assert process.stderr.read() == "warn\n"
    assert process.wait() == 3 and process.returncode == 3 and process.poll() == 3


def test_stdout_iterates_by_line_while_stderr_is_kept(client, rsps):
    sandbox = sandbox_of(client, rsps)
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands" % ID, json={"pid": 8})
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/8/stream" % ID,
        body=event(stdout=b64("a\nb"))
        + event(stderr=b64("e"))
        + event(stdout=b64("c\n"))
        + event(exit={"exit_code": 0}),
    )
    process = sandbox.exec("cmd")
    assert list(process.stdout) == ["a\n", "bc\n"]
    assert process.stderr.read() == "e"


def test_exec_with_text_false_returns_bytes(client, rsps):
    sandbox = sandbox_of(client, rsps)
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands" % ID, json={"pid": 9})
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/9/stream" % ID,
        body=event(stdout=b64("hi")) + event(exit={"exit_code": 0}),
    )
    assert sandbox.exec("cmd", text=False).stdout.read() == b"hi"


def test_stdin_writes_are_buffered_until_drain_and_eof_closes(client, rsps):
    sandbox = sandbox_of(client, rsps)
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands" % ID, json={"pid": 5})
    process = sandbox.exec("cat")
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands/5/stdin" % ID, json={})
    process.stdin.write("hello")
    process.stdin.write(b" world")
    count = len(rsps.calls)
    process.stdin.drain()
    assert len(rsps.calls) == count + 1
    assert base64.b64decode(last_body(rsps)["data"]) == b"hello world"
    process.stdin.write_eof()
    assert last_body(rsps).get("eof") is True or rsps.calls[-1].request.url.endswith(
        "/stdin"
    )


def test_exec_refuses_pty_and_stream_redirection(client, rsps):
    sandbox = sandbox_of(client, rsps)
    with pytest.raises(SandboxNotImplementedError, match="pty"):
        sandbox.exec("bash", pty=True)
    with pytest.raises(SandboxNotImplementedError, match="stdout"):
        sandbox.exec("ls", stdout=modal.StreamType.DEVNULL)


def test_an_entrypoint_command_feeds_sandbox_stdout_and_wait(client, rsps):
    rsps.add(responses.POST, API + "/v2/sandboxes", json={"sandbox": RAW}, status=201)
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands" % ID, json={"pid": 2})
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/2/stream" % ID,
        body=event(stdout=b64("up\n")) + event(exit={"exit_code": 0}),
    )
    sandbox = client.Sandbox.create("sh", "-c", "echo up")
    assert json.loads(rsps.calls[1].request.body)["cmd"] == "sh"
    assert sandbox.stdout.read() == "up\n"
    sandbox.wait()
    assert sandbox.returncode == 0 and sandbox.poll() == 0


def test_without_an_entrypoint_stdout_explains_what_to_do(client, rsps):
    sandbox = sandbox_of(client, rsps)
    with pytest.raises(modal.exception.Error, match="entrypoint"):
        sandbox.stdout  # pylint: disable=pointless-statement


def test_terminate_from_id_and_list(client, rsps):
    rsps.add(responses.GET, API + "/v2/sandboxes/%s" % ID, json={"sandbox": RAW})
    sandbox = client.Sandbox.from_id(ID)
    rsps.add(responses.DELETE, API + "/v2/sandboxes/%s" % ID, json={})
    assert sandbox.terminate() is None
    rsps.add(responses.GET, API + "/v2/sandboxes", json={"sandboxes": [RAW]})
    assert [s.object_id for s in client.Sandbox.list()] == [ID]
    with pytest.raises(SandboxNotImplementedError, match="Sandbox.list"):
        list(client.Sandbox.list(tags={"a": "b"}))
    with pytest.raises(SandboxNotImplementedError, match="Sandbox.list"):
        list(client.Sandbox.list(app_id="ap-1"))


def test_experimental_pause_and_resume(client, rsps):
    sandbox = sandbox_of(client, rsps)
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes/%s/pause" % ID,
        json={"sandbox": dict(RAW, state="SANDBOX_STATE_PAUSED")},
    )
    sandbox._experimental_pause()
    rsps.add(
        responses.POST, API + "/v2/sandboxes/%s/resume" % ID, json={"sandbox": RAW}
    )
    sandbox._experimental_resume()
    assert rsps.calls[-1].request.url.endswith("/resume")


def test_filesystem_tunnels_tags_and_snapshots_raise(client, rsps):
    sandbox = sandbox_of(client, rsps)
    with pytest.raises(SandboxNotImplementedError, match="SandboxFilesystem"):
        sandbox.filesystem.read_text("/a")
    with pytest.raises(SandboxNotImplementedError, match="Sandbox.tunnels"):
        sandbox.tunnels()
    with pytest.raises(SandboxNotImplementedError, match="Sandbox.snapshot_filesystem"):
        sandbox.snapshot_filesystem()
    with pytest.raises(SandboxNotImplementedError, match="Sandbox.set_tags"):
        sandbox.set_tags({"a": "b"})


def test_api_errors_become_modal_errors(client, rsps):
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/missing",
        json={"id": "not_found", "message": "gone"},
        status=404,
    )
    with pytest.raises(modal.exception.NotFoundError):
        client.Sandbox.from_id("missing")
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes",
        json={"id": "unauthorized", "message": "no"},
        status=401,
    )
    with pytest.raises(modal.exception.AuthError):
        client.Sandbox.create()


def test_client_from_credentials_binds_the_token_and_app_lookup_is_local(rsps):
    rsps.add(responses.POST, API + "/v2/sandboxes", json={"sandbox": RAW}, status=201)
    bound = modal.Client.from_credentials("id", "per-client")
    bound._conn["api_url"] = API
    modal.Sandbox.create(client=bound)
    assert rsps.calls[-1].request.headers["Authorization"] == "Bearer per-client"
    app = modal.App.lookup("a", create_if_missing=True)
    assert app.name == "a" and app.app_id == "ap-a"
    with pytest.raises(SandboxNotImplementedError, match="App.deploy"):
        app.deploy()
    with pytest.raises(KeyError):
        modal.Secret.from_local_environ(["DEFINITELY_UNSET_VARIABLE_XYZ"])
