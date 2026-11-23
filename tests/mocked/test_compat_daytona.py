# pylint: disable=missing-function-docstring,redefined-outer-name
"""Mocked tests for the Daytona compat client (``pydo.sandbox.compat.daytona``).

Runs through the real sync pipeline with ``responses``.
"""

import base64
import json

import pytest
import responses

from pydo.sandbox import SandboxNotImplementedError
from pydo.sandbox.compat import daytona

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


def tpl(status="TEMPLATE_STATUS_READY", template_id="t-1", name="my-snap"):
    return {
        "template_id": template_id,
        "name": name,
        "status": status,
        "spec": {
            "base_template": "coding-base",
            "image": {
                "registry": "docker.io",
                "repository": "library/python",
                "tag": "3.12",
            },
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
    return daytona.Daytona(daytona.DaytonaConfig(api_key="test-token"), do_api_url=API)


def last_body(rsps):
    return json.loads(rsps.calls[-1].request.body)


def sandbox_of(client, rsps):
    rsps.add(responses.POST, API + "/v2/sandboxes", json={"sandbox": RAW}, status=201)
    return client.create()


def test_create_defaults_use_the_default_template(client, rsps):
    sandbox = sandbox_of(client, rsps)
    assert last_body(rsps) == {"template": "coding-base", "size_slug": "mars-2vcpu-4gb"}
    assert rsps.calls[-1].request.headers["Authorization"] == "Bearer test-token"
    assert sandbox.id == ID and sandbox.state == daytona.SandboxState.STARTED
    assert sandbox.snapshot == "coding-base"


def test_create_from_snapshot_params_maps_to_the_template_env_and_network(client, rsps):
    rsps.add(responses.POST, API + "/v2/sandboxes", json={"sandbox": RAW}, status=201)
    client.create(
        daytona.CreateSandboxFromSnapshotParams(
            snapshot="my-snap", env_vars={"A": "1"}, network_block_all=True
        )
    )
    assert last_body(rsps) == {
        "template": "my-snap",
        "size_slug": "mars-2vcpu-4gb",
        "allow_internet_access": False,
        "env_vars": {"A": "1"},
    }


@pytest.mark.parametrize(
    "params",
    [
        daytona.CreateSandboxFromImageParams(image="python:3.12"),
        daytona.CreateSandboxFromSnapshotParams(language="python"),
        daytona.CreateSandboxFromSnapshotParams(labels={"a": "b"}),
        daytona.CreateSandboxFromSnapshotParams(auto_stop_interval=0),
        daytona.CreateSandboxFromSnapshotParams(volumes=[object()]),
        daytona.CreateSandboxFromSnapshotParams(network_allow_list="1.2.3.4"),
        daytona.CreateSandboxFromSnapshotParams(name="mine"),
        daytona.CreateSandboxFromSnapshotParams(ephemeral=True),
    ],
)
def test_create_refuses_options_it_cannot_honor_before_any_request(
    client, rsps, params
):
    with pytest.raises(SandboxNotImplementedError, match="Daytona.create"):
        client.create(params)
    assert not rsps.calls


@pytest.mark.parametrize(
    "config",
    [
        {"target": "us"},
        {"organization_id": "org"},
        {"jwt_token": "j"},
        {"api_url": "https://app.daytona.io/api"},
    ],
)
def test_config_fields_that_point_at_daytona_raise(config):
    with pytest.raises(SandboxNotImplementedError, match="not supported"):
        daytona.Daytona(daytona.DaytonaConfig(api_key="x", **config))


def test_http_tuning_in_the_config_is_accepted():
    daytona.Daytona(
        daytona.DaytonaConfig(
            api_key="x", connection_pool_maxsize=3, otel_enabled=False
        )
    )


def test_process_exec_returns_the_output_and_does_not_raise_on_failure(client, rsps):
    sandbox = sandbox_of(client, rsps)
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands" % ID, json={"pid": 7})
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/7/stream" % ID,
        body=event(stdout=b64("out\n"))
        + event(stderr=b64("err\n"))
        + event(exit={"exit_code": 2}),
    )
    result = sandbox.process.exec("make", cwd="/w", env={"K": "v"}, timeout=30)
    assert result.exit_code == 2 and result.result == "out\nerr\n"
    body = json.loads(rsps.calls[-2].request.body)
    assert body["cmd"] == "bash" and body["args"] == ["-lc", "make"]
    assert (
        body["cwd"] == "/w"
        and body["env_vars"] == {"K": "v"}
        and body["timeout_seconds"] == "30"
    )


def test_stop_start_pause_and_delete_map_to_pause_resume_and_kill(client, rsps):
    sandbox = sandbox_of(client, rsps)
    rsps.add(
        responses.POST, API + "/v2/sandboxes/%s/pause" % ID, json={"sandbox": PAUSED}
    )
    client.stop(sandbox)
    assert sandbox.state == daytona.SandboxState.STOPPED
    rsps.add(
        responses.POST, API + "/v2/sandboxes/%s/resume" % ID, json={"sandbox": RAW}
    )
    client.start(sandbox)
    assert sandbox.state == daytona.SandboxState.STARTED
    rsps.add(responses.DELETE, API + "/v2/sandboxes/%s" % ID, json={})
    client.delete(sandbox)
    assert rsps.calls[-1].request.method == "DELETE"


def test_get_and_list_with_state_filter(client, rsps):
    rsps.add(responses.GET, API + "/v2/sandboxes/%s" % ID, json={"sandbox": RAW})
    assert client.get(ID).id == ID
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes",
        json={"sandboxes": [RAW, dict(RAW, sandbox_id="sb-2")]},
    )
    found = list(
        client.list(
            daytona.ListSandboxesQuery(states=[daytona.SandboxState.STARTED], limit=2)
        )
    )
    assert [s.id for s in found] == [ID, "sb-2"]
    assert "state=SANDBOX_STATE_RUNNING" in rsps.calls[-1].request.url


def test_list_refuses_filters_the_api_lacks(client):
    with pytest.raises(SandboxNotImplementedError, match="Daytona.list"):
        client.list(daytona.ListSandboxesQuery(labels={"a": "b"}))


def test_api_errors_become_daytona_errors(client, rsps):
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/missing",
        json={"id": "not_found", "message": "no such sandbox"},
        status=404,
    )
    with pytest.raises(daytona.DaytonaNotFoundError) as err:
        client.get("missing")
    assert err.value.status_code == 404 and isinstance(err.value, daytona.DaytonaError)
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes",
        json={"id": "x", "message": "slow down"},
        status=429,
        headers={"Retry-After": "0"},
    )
    with pytest.raises(daytona.DaytonaRateLimitError):
        client.create()


def test_sandbox_create_snapshot_waits_for_the_digitalocean_snapshot(client, rsps):
    sandbox = sandbox_of(client, rsps)
    snap = {
        "snapshot_id": "sn-1",
        "sandbox_id": ID,
        "name": "mine",
        "state": "SNAPSHOT_STATE_CREATING",
        "created_at": "2026-11-20T12:00:00Z",
    }
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes/%s/snapshots" % ID,
        json={"snapshot": snap},
        status=202,
    )
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/snapshots/sn-1",
        json={"snapshot": dict(snap, state="SNAPSHOT_STATE_COMPLETE")},
    )
    sandbox.create_snapshot("mine")
    assert json.loads(rsps.calls[-2].request.body) == {"name": "mine"}


def test_snapshot_service_maps_to_templates(client, rsps):
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes/templates",
        json={"template": tpl("TEMPLATE_STATUS_PENDING")},
        status=201,
    )
    rsps.add(
        responses.GET, API + "/v2/sandboxes/templates/t-1", json={"template": tpl()}
    )
    created = client.snapshot.create(
        daytona.CreateSnapshotParams(name="my-snap", image="python:3.12")
    )
    assert created.name == "my-snap" and created.state == daytona.SnapshotState.ACTIVE
    post = json.loads(rsps.calls[0].request.body)
    assert post["name"] == "my-snap" and post["source_oci_ref"] == "python:3.12"
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/templates",
        json={"templates": [tpl(), tpl(template_id="t-2", name="other")]},
    )
    page = client.snapshot.list(page=1, limit=1)
    assert (
        [s.name for s in page.items] == ["my-snap"]
        and page.total == 2
        and page.total_pages == 2
    )
    assert client.snapshot.get("other").id == "t-2"
    with pytest.raises(daytona.DaytonaNotFoundError):
        client.snapshot.get("nope")
    rsps.add(responses.DELETE, API + "/v2/sandboxes/templates/t-1", json={})
    client.snapshot.delete("my-snap")


def test_snapshot_create_refuses_image_builders_and_resources(client):
    with pytest.raises(SandboxNotImplementedError, match="Image builder"):
        client.snapshot.create(daytona.CreateSnapshotParams(name="x", image=object()))
    with pytest.raises(SandboxNotImplementedError, match="resources"):
        client.snapshot.create(
            daytona.CreateSnapshotParams(
                name="x", image="python:3.12", resources=object()
            )
        )


def test_v2_namespace_creates_from_a_snapshot_and_execs(client, rsps):
    v2 = client.v2
    rsps.add(responses.POST, API + "/v2/sandboxes", json={"sandbox": RAW}, status=201)
    sandbox = v2.create_from_snapshot("my-snap")
    assert last_body(rsps)["template"] == "my-snap"
    assert sandbox.id == ID and sandbox.state == "started"
    rsps.add(responses.POST, API + "/v2/sandboxes/%s/commands" % ID, json={"pid": 3})
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes/%s/commands/3/stream" % ID,
        body=event(stdout=b64("hi")) + event(exit={"exit_code": 0}),
    )
    result = sandbox.exec("echo hi")
    assert result.stdout == "hi" and result.exit_code == 0 and result.reason == "exited"
    with pytest.raises(SandboxNotImplementedError, match="create\\(image"):
        v2.create("python:3.12")
    rsps.add(
        responses.POST, API + "/v2/sandboxes/%s/pause" % ID, json={"sandbox": PAUSED}
    )
    v2.pause(sandbox)
    rsps.add(
        responses.GET,
        API + "/v2/sandboxes",
        json={"sandboxes": [RAW], "next_page_token": "t2"},
    )
    page = v2.list(limit=1)
    assert [s.id for s in page.items] == [ID] and page.next_cursor == "t2"


def test_files_git_and_lsp_raise_on_use(client, rsps):
    sandbox = sandbox_of(client, rsps)
    with pytest.raises(SandboxNotImplementedError, match="FileSystem"):
        sandbox.fs.upload_file(b"x", "/a")
    with pytest.raises(SandboxNotImplementedError, match="Git"):
        sandbox.git.clone("u", "p")
    with pytest.raises(SandboxNotImplementedError, match="Sandbox.get_preview_link"):
        sandbox.get_preview_link(80)


def test_root_client_delegates_the_legacy_calls_to_v0(client, rsps):
    rsps.add(responses.GET, API + "/v2/sandboxes/%s" % ID, json={"sandbox": RAW})
    assert client.get(ID).id == ID
    assert client.v0.get(ID).id == ID
