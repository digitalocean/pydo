# pylint: disable=missing-function-docstring,redefined-outer-name,duplicate-code,unexpected-keyword-arg
"""Mocked tests for sandbox snapshots (``pydo.sandbox``), through the real pipeline."""

import json

import pytest
import responses

from pydo.sandbox import (
    NotFoundError,
    Sandbox,
    SandboxClient,
    SandboxError,
    SandboxTimeoutError,
    Snapshot,
)

API = "https://sandbox.test"
CONN = {"token": "test-token", "api_url": API}
BASE = API + "/v2/sandboxes/snapshots"


def snap(state="SNAPSHOT_STATE_COMPLETE", snapshot_id="s-1", **extra):
    out = {
        "snapshot_id": snapshot_id,
        "sandbox_id": "sb-1",
        "name": "my-snapshot",
        "state": state,
        "size_bytes": "1073741824",
        "created_at": "2026-11-20T12:00:00Z",
        "ttl": "168h",
    }
    out.update(extra)
    return out


def sandbox_raw():
    return {
        "sandbox_id": "sb-1",
        "template": "coding-base",
        "state": "SANDBOX_STATE_RUNNING",
        "created_at": "2026-11-20T12:00:00Z",
    }


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("DIGITALOCEAN_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("DIGITALOCEAN_API_URL", raising=False)


@pytest.fixture
def rsps():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        yield mock


def body_of(mock, index=-1):
    return json.loads(mock.calls[index].request.body)


def test_create_sends_name_and_ttl_and_accepts_202(rsps):
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes/sb-1/snapshots",
        json={"snapshot": snap("SNAPSHOT_STATE_CREATING", size_bytes="")},
        status=202,
    )
    snapshot = Snapshot.create("sb-1", name="my-snapshot", ttl="168h", **CONN)
    assert body_of(rsps) == {"name": "my-snapshot", "ttl": "168h"}
    assert (snapshot.snapshot_id, snapshot.sandbox_id, snapshot.name) == (
        "s-1",
        "sb-1",
        "my-snapshot",
    )
    assert snapshot.state == "SNAPSHOT_STATE_CREATING"
    assert snapshot.info.size_bytes is None
    assert snapshot.info.ttl == "168h"


def test_create_without_options_sends_no_body_and_accepts_200(rsps):
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes/sb-1/snapshots",
        json={"snapshot": snap()},
        status=200,
    )
    snapshot = Snapshot.create("sb-1", **CONN)
    assert not rsps.calls[0].request.body
    assert snapshot.info.size_bytes == 1073741824
    assert snapshot.info.created_at.year == 2026


def test_create_validates_before_sending(rsps):
    for bad in ("Upper", "has space", "", "x" * 64, "under_score"):
        with pytest.raises(SandboxError, match="name"):
            Snapshot.create("sb-1", name=bad, **CONN)
    with pytest.raises(SandboxError, match="ttl"):
        Snapshot.create("sb-1", ttl=" ", **CONN)
    with pytest.raises(SandboxError, match="sandbox_id"):
        Snapshot.create("", **CONN)
    with pytest.raises(TypeError):
        Snapshot.create(
            "sb-1", timeout=5, **CONN
        )  # pylint: disable=unexpected-keyword-arg
    assert len(rsps.calls) == 0


def test_sandbox_create_snapshot_shares_the_sandbox_connection(rsps):
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes",
        json={"sandbox": sandbox_raw()},
        status=201,
    )
    sandbox = Sandbox.create(template="coding-base", **CONN)
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes/sb-1/snapshots",
        json={"snapshot": snap("SNAPSHOT_STATE_CREATING")},
        status=202,
    )
    snapshot = sandbox.create_snapshot(name="before-upgrade")
    assert body_of(rsps) == {"name": "before-upgrade"}
    assert snapshot.sandbox_id == "sb-1"
    snapshot.close()
    rsps.add(responses.GET, API + "/v2/sandboxes/sb-1", json={"sandbox": sandbox_raw()})
    assert sandbox.get_info().sandbox_id == "sb-1"
    with pytest.raises(SandboxError, match="name"):
        sandbox.create_snapshot(name="Bad Name")


def test_get_and_refresh(rsps):
    rsps.add(
        responses.GET,
        BASE + "/s-1",
        json={"snapshot": snap("SNAPSHOT_STATE_UPLOADING")},
    )
    snapshot = Snapshot.get("s-1", **CONN)
    assert snapshot.state == "SNAPSHOT_STATE_UPLOADING"
    rsps.add(responses.GET, BASE + "/s-1", json={"snapshot": snap()})
    assert snapshot.refresh().state == "SNAPSHOT_STATE_COMPLETE"


def test_get_raises_a_typed_error_for_an_unknown_snapshot(rsps):
    rsps.add(
        responses.GET,
        BASE + "/nope",
        json={"id": "not_found", "message": "no such snapshot", "request_id": "r"},
        status=404,
    )
    with pytest.raises(NotFoundError) as info:
        Snapshot.get("nope", **CONN)
    assert info.value.request_id == "r"


def test_delete_by_id_and_on_the_instance(rsps):
    rsps.add(responses.DELETE, BASE + "/s-1", json={})
    assert Snapshot.delete("s-1", **CONN) is True
    rsps.add(
        responses.DELETE,
        BASE + "/gone",
        json={"id": "not_found", "message": "gone"},
        status=404,
    )
    assert Snapshot.delete("gone", **CONN) is False
    rsps.add(responses.GET, BASE + "/s-1", json={"snapshot": snap()})
    assert Snapshot.get("s-1", **CONN).delete() is True


def test_list_filters_by_sandbox_and_walks_every_page(rsps):
    rsps.add(
        responses.GET,
        BASE,
        json={"snapshots": [snap(snapshot_id="a")], "next_page_token": "t2"},
    )
    rsps.add(responses.GET, BASE, json={"snapshots": [snap(snapshot_id="b")]})
    ids = [s.snapshot_id for s in Snapshot.list(sandbox_id="sb-1", limit=1, **CONN)]
    assert ids == ["a", "b"]
    assert "sandbox_id=sb-1" in rsps.calls[0].request.url
    assert "page_size=1" in rsps.calls[0].request.url
    assert "page_token=t2" in rsps.calls[1].request.url


def test_list_one_page_at_a_time(rsps):
    rsps.add(responses.GET, BASE, json={"snapshots": [snap()], "next_page_token": "t2"})
    pages = Snapshot.list(**CONN)
    assert pages.has_next
    assert len(pages.next_items()) == 1
    assert pages.next_token == "t2"


def test_wait_until_ready_polls_until_complete(rsps):
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes/sb-1/snapshots",
        json={"snapshot": snap("SNAPSHOT_STATE_CREATING")},
        status=202,
    )
    snapshot = Snapshot.create("sb-1", **CONN)
    rsps.add(
        responses.GET,
        BASE + "/s-1",
        json={"snapshot": snap("SNAPSHOT_STATE_UPLOADING")},
    )
    rsps.add(responses.GET, BASE + "/s-1", json={"snapshot": snap()})
    assert snapshot.wait_until_ready(poll_interval=0.01) is snapshot
    assert snapshot.state == "SNAPSHOT_STATE_COMPLETE"
    assert len(rsps.calls) == 3


def test_wait_until_ready_explains_a_failed_snapshot(rsps):
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes/sb-1/snapshots",
        json={"snapshot": snap("SNAPSHOT_STATE_CREATING")},
        status=202,
    )
    snapshot = Snapshot.create("sb-1", **CONN)
    rsps.add(
        responses.GET,
        BASE + "/s-1",
        json={
            "snapshot": snap(
                "SNAPSHOT_STATE_FAILED", error_message="disk capture timed out"
            )
        },
    )
    with pytest.raises(SandboxError, match="s-1 failed: disk capture timed out"):
        snapshot.wait_until_ready(poll_interval=0.01)


def test_wait_until_ready_times_out(rsps):
    rsps.add(
        responses.GET, BASE + "/s-1", json={"snapshot": snap("SNAPSHOT_STATE_CREATING")}
    )
    snapshot = Snapshot.get("s-1", **CONN)
    with pytest.raises(SandboxTimeoutError, match="not complete in time"):
        snapshot.wait_until_ready(timeout=0.05, poll_interval=0.01)


def test_sandbox_client_binds_the_token(rsps):
    client = SandboxClient(**CONN)
    rsps.add(responses.GET, BASE + "/s-1", json={"snapshot": snap()})
    assert client.Snapshot.get("s-1").snapshot_id == "s-1"
    assert rsps.calls[0].request.headers["Authorization"] == "Bearer test-token"
    rsps.add(responses.DELETE, BASE + "/s-1", json={})
    assert client.Snapshot.delete("s-1") is True
    rsps.add(responses.GET, BASE, json={"snapshots": [snap()]})
    assert [s.snapshot_id for s in client.Snapshot.list(sandbox_id="sb-1")] == ["s-1"]
