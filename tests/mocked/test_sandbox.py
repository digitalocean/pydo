# pylint: disable=missing-function-docstring,redefined-outer-name,duplicate-code,import-outside-toplevel,invalid-name,unexpected-keyword-arg,line-too-long
"""Mocked tests for the Sandbox SDK (``pydo.sandbox``)."""

import json

import pytest
import responses

from pydo.sandbox import (
    AuthenticationError,
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    RateLimitError,
    Sandbox,
    SandboxClient,
    SandboxError,
)

API = "https://sandbox.test"
CONN = {"token": "test-token", "api_url": API}


def raw(sandbox_id, state="SANDBOX_STATE_RUNNING"):
    return {
        "sandbox_id": sandbox_id,
        "template": "coding-base",
        "state": state,
        "size_slug": "mars-2vcpu-4gb",
        "created_at": "2026-11-20T12:00:00Z",
    }


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("DIGITALOCEAN_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("DIGITALOCEAN_API_URL", raising=False)


@responses.activate
def test_create_sends_body_and_returns_sandbox():
    responses.add(
        responses.POST, API + "/v2/sandboxes", json={"sandbox": raw("sb-1")}, status=201
    )
    sb = Sandbox.create(
        template="coding-base",
        size="s-1vcpu-2gb",
        allow_internet_access=False,
        env_vars={"A": "1"},
        **CONN,
    )
    assert json.loads(responses.calls[0].request.body) == {
        "template": "coding-base",
        "size_slug": "s-1vcpu-2gb",
        "allow_internet_access": False,
        "env_vars": {"A": "1"},
    }
    assert responses.calls[0].request.headers["Authorization"] == "Bearer test-token"
    assert sb.sandbox_id == "sb-1"
    assert sb.state == "SANDBOX_STATE_RUNNING"
    assert sb.info.created_at.year == 2026


@responses.activate
def test_create_defaults_size():
    responses.add(
        responses.POST, API + "/v2/sandboxes", json={"sandbox": raw("sb-1")}, status=201
    )
    Sandbox.create(template="coding-base", **CONN)
    assert json.loads(responses.calls[0].request.body) == {
        "template": "coding-base",
        "size_slug": "mars-2vcpu-4gb",
    }


@responses.activate
def test_create_defaults_the_template():
    responses.add(
        responses.POST, API + "/v2/sandboxes", json={"sandbox": raw("sb-1")}, status=201
    )
    Sandbox.create(**CONN)
    assert json.loads(responses.calls[0].request.body) == {
        "template": "coding-base",
        "size_slug": "mars-2vcpu-4gb",
    }


def test_create_validates_before_sending():
    with pytest.raises(SandboxError, match="template"):
        Sandbox.create(template="", **CONN)
    with pytest.raises(TypeError):
        Sandbox.create(
            template="coding-base", timeout=5, **CONN
        )  # pylint: disable=unexpected-keyword-arg
    with pytest.raises(AuthenticationError, match="DIGITALOCEAN_ACCESS_TOKEN"):
        Sandbox.create(template="coding-base")


@responses.activate
def test_token_and_url_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("DIGITALOCEAN_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("DIGITALOCEAN_API_URL", API)
    responses.add(
        responses.GET, API + "/v2/sandboxes/sb-1", json={"sandbox": raw("sb-1")}
    )
    Sandbox.get("sb-1")
    assert responses.calls[0].request.headers["Authorization"] == "Bearer test-token"


@responses.activate
def test_pause_resume_kill():
    responses.add(
        responses.GET, API + "/v2/sandboxes/sb-1", json={"sandbox": raw("sb-1")}
    )
    sb = Sandbox.get("sb-1", **CONN)
    responses.add(
        responses.POST,
        API + "/v2/sandboxes/sb-1/pause",
        json={"sandbox": raw("sb-1", "SANDBOX_STATE_PAUSED")},
    )
    assert sb.pause().state == "SANDBOX_STATE_PAUSED"
    responses.add(
        responses.POST, API + "/v2/sandboxes/sb-1/resume", json={"sandbox": raw("sb-1")}
    )
    sb.resume()
    assert sb.state == "SANDBOX_STATE_RUNNING"
    responses.add(responses.DELETE, API + "/v2/sandboxes/sb-1", json={})
    assert sb.kill() is True


@responses.activate
def test_by_id_kill_and_pause_on_the_class():
    responses.add(responses.DELETE, API + "/v2/sandboxes/sb-1", json={})
    assert Sandbox.kill("sb-1", **CONN) is True
    responses.add(
        responses.POST,
        API + "/v2/sandboxes/sb-2/pause",
        json={"sandbox": raw("sb-2", "SANDBOX_STATE_PAUSED")},
    )
    assert Sandbox.pause("sb-2", **CONN).state == "SANDBOX_STATE_PAUSED"


@responses.activate
def test_kill_returns_false_when_gone():
    responses.add(
        responses.DELETE,
        API + "/v2/sandboxes/gone",
        json={"id": "not_found", "message": "Sandbox not found for your team."},
        status=404,
    )
    assert Sandbox.kill("gone", **CONN) is False


@responses.activate
def test_connect_resumes_a_paused_sandbox():
    responses.add(
        responses.GET,
        API + "/v2/sandboxes/sb-1",
        json={"sandbox": raw("sb-1", "SANDBOX_STATE_PAUSED")},
    )
    responses.add(
        responses.POST, API + "/v2/sandboxes/sb-1/resume", json={"sandbox": raw("sb-1")}
    )
    assert Sandbox.connect("sb-1", **CONN).state == "SANDBOX_STATE_RUNNING"


@responses.activate
def test_list_walks_every_page_and_passes_filters():
    responses.add(
        responses.GET,
        API + "/v2/sandboxes",
        json={"sandboxes": [raw("a")], "next_page_token": "t2"},
    )
    responses.add(responses.GET, API + "/v2/sandboxes", json={"sandboxes": [raw("b")]})
    ids = [
        s.sandbox_id
        for s in Sandbox.list(state="SANDBOX_STATE_RUNNING", limit=1, **CONN)
    ]
    assert ids == ["a", "b"]
    first, second = (c.request.url for c in responses.calls)
    assert "page_size=1" in first and "state=SANDBOX_STATE_RUNNING" in first
    assert "page_token=t2" in second


@responses.activate
def test_list_one_page_at_a_time():
    responses.add(
        responses.GET,
        API + "/v2/sandboxes",
        json={"sandboxes": [raw("a")], "next_page_token": "t2"},
    )
    pages = Sandbox.list(**CONN)
    assert pages.has_next
    assert [s.sandbox_id for s in pages.next_items()] == ["a"]
    assert pages.next_token == "t2"


@responses.activate
def test_errors_are_typed():
    body = {"id": "not_found", "message": "Template not found.", "request_id": "req-1"}
    responses.add(responses.POST, API + "/v2/sandboxes", json=body, status=404)
    with pytest.raises(NotFoundError) as info:
        Sandbox.create(template="nope", **CONN)
    assert info.value.status == 404
    assert info.value.code == "not_found"
    assert info.value.request_id == "req-1"
    assert "Template not found" in str(info.value)

    responses.replace(
        responses.POST,
        API + "/v2/sandboxes",
        json={"id": "x", "message": "m"},
        status=409,
    )
    with pytest.raises(ConflictError):
        Sandbox.create(template="b", **CONN)
    responses.replace(
        responses.POST,
        API + "/v2/sandboxes",
        json={"id": "x", "message": "m"},
        status=401,
    )
    with pytest.raises(AuthenticationError):
        Sandbox.create(template="b", **CONN)
    responses.replace(
        responses.POST,
        API + "/v2/sandboxes",
        json={"id": "x", "message": "slow down"},
        status=429,
        headers={"Retry-After": "1"},
    )
    with pytest.raises(RateLimitError) as limited:
        Sandbox.create(template="b", **CONN)
    assert limited.value.retry_after == 1
    responses.add(
        responses.POST,
        API + "/v2/sandboxes/sb-1/pause",
        json={"id": "bad_request", "message": "cannot be paused"},
        status=400,
    )
    with pytest.raises(InvalidRequestError):
        Sandbox.pause("sb-1", **CONN)
    assert issubclass(NotFoundError, SandboxError)


@responses.activate
def test_sandbox_client_binds_options():
    responses.add(
        responses.POST, API + "/v2/sandboxes", json={"sandbox": raw("sb-1")}, status=201
    )
    sb = SandboxClient(**CONN).Sandbox.create(template="coding-base")
    assert sb.sandbox_id == "sb-1"


@responses.activate
def test_context_manager_kills_the_sandbox():
    responses.add(
        responses.POST, API + "/v2/sandboxes", json={"sandbox": raw("sb-1")}, status=201
    )
    responses.add(responses.DELETE, API + "/v2/sandboxes/sb-1", json={})
    with Sandbox.create(template="coding-base", **CONN):
        pass
    assert responses.calls[-1].request.method == "DELETE"


@responses.activate
def test_wait_until_running_polls_a_creating_sandbox():
    responses.add(
        responses.GET,
        API + "/v2/sandboxes/sb-1",
        json={"sandbox": raw("sb-1", "SANDBOX_STATE_CREATING")},
    )
    sb = Sandbox.get("sb-1", **CONN)
    responses.replace(
        responses.GET, API + "/v2/sandboxes/sb-1", json={"sandbox": raw("sb-1")}
    )
    sb.wait_until_running(poll_interval=0.01)
    assert sb.state == "SANDBOX_STATE_RUNNING"


def test_import_pydo_does_not_load_the_sandbox_package():
    import subprocess
    import sys

    out = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, pydo; print('pydo.sandbox' in sys.modules)",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.strip() == "False"


def test_sandbox_is_importable_from_the_package_root_and_loads_lazily():
    import subprocess
    import sys

    code = (
        "import sys, pydo, pydo.aio\n"
        "assert 'pydo.sandbox' not in sys.modules and 'pydo.aio.sandbox' not in sys.modules\n"
        "from pydo import Sandbox, SandboxClient\n"
        "from pydo.aio import Sandbox as AioSandbox\n"
        "import pydo.sandbox, pydo.aio.sandbox\n"
        "assert Sandbox is pydo.sandbox.Sandbox and AioSandbox is pydo.aio.sandbox.Sandbox\n"
        "assert Sandbox is not AioSandbox\n"
        "try:\n"
        "    pydo.NoSuchThing\n"
        "except AttributeError:\n"
        "    print('ok')\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "ok"


def test_a_missing_sandbox_package_only_breaks_sandbox():
    import subprocess
    import sys

    code = (
        "import sys\n"
        "sys.modules['pydo.sandbox'] = None\n"  # makes `import pydo.sandbox` raise ImportError
        "import pydo\n"
        "pydo.Client('t')\n"
        "try:\n"
        "    pydo.Sandbox\n"
        "except AttributeError as e:\n"
        "    print('could not be imported' in str(e))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "True"
