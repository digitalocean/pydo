# pylint: disable=missing-function-docstring,redefined-outer-name
"""Mocked tests for sandbox templates (``pydo.sandbox``), through the real pipeline."""

import json

import pytest
import responses

from pydo.sandbox import (
    NotFoundError,
    Sandbox,
    SandboxClient,
    SandboxError,
    Template,
)

API = "https://sandbox.test"
CONN = {"token": "test-token", "api_url": API}
BASE = API + "/v2/sandboxes/templates"


def tpl(status="TEMPLATE_STATUS_READY", template_id="t-1"):
    return {
        "template_id": template_id,
        "name": "my-template",
        "status": status,
        "spec": {
            "base_template": "coding-base",
            "image": {
                "registry": "registry.digitalocean.com",
                "repository": "my-team/my-image",
                "tag": "v1",
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


def body_of(mock, index=-1):
    return json.loads(mock.calls[index].request.body)


def test_create_sends_name_base_and_image(rsps):
    rsps.add(
        responses.POST,
        BASE,
        json={"template": tpl("TEMPLATE_STATUS_PENDING")},
        status=201,
    )
    template = Template.create(
        name="my-template",
        source_oci_ref="registry.digitalocean.com/my-team/my-image:v1",
        **CONN
    )
    assert body_of(rsps) == {
        "name": "my-template",
        "base_template": "coding-base",
        "source_oci_ref": "registry.digitalocean.com/my-team/my-image:v1",
    }
    assert (template.template_id, template.name, template.status) == (
        "t-1",
        "my-template",
        "TEMPLATE_STATUS_PENDING",
    )
    assert template.info.base_template == "coding-base"
    assert template.info.image.repository == "my-team/my-image"
    assert template.info.created_at.year == 2026


def test_create_validates_before_sending(rsps):
    with pytest.raises(SandboxError, match="name"):
        Template.create(name="", source_oci_ref="r", **CONN)
    with pytest.raises(SandboxError, match="source_oci_ref"):
        Template.create(name="n", source_oci_ref=" ", **CONN)
    with pytest.raises(TypeError):
        Template.create(
            name="n", source_oci_ref="r", timeout=5, **CONN
        )  # pylint: disable=unexpected-keyword-arg
    assert len(rsps.calls) == 0


def test_update_sends_only_what_changed(rsps):
    rsps.add(responses.GET, BASE + "/t-1", json={"template": tpl()})
    template = Template.get("t-1", **CONN)
    rsps.add(
        responses.PUT, BASE + "/t-1", json={"template": tpl("TEMPLATE_STATUS_BUILDING")}
    )
    template.update(source_oci_ref="r/i:v2")
    assert body_of(rsps) == {"source_oci_ref": "r/i:v2"}
    assert template.status == "TEMPLATE_STATUS_BUILDING"
    with pytest.raises(SandboxError, match="source_oci_ref"):
        template.update()


def test_delete_by_id_and_on_the_instance(rsps):
    rsps.add(responses.DELETE, BASE + "/t-1", json={})
    assert Template.delete("t-1", **CONN) is True
    rsps.add(
        responses.DELETE,
        BASE + "/gone",
        json={"id": "not_found", "message": "gone"},
        status=404,
    )
    assert Template.delete("gone", **CONN) is False
    rsps.add(responses.GET, BASE + "/t-1", json={"template": tpl()})
    assert Template.get("t-1", **CONN).delete() is True


def test_get_raises_a_typed_error_for_an_unknown_template(rsps):
    rsps.add(
        responses.GET,
        BASE + "/nope",
        json={"id": "not_found", "message": "no such template", "request_id": "r"},
        status=404,
    )
    with pytest.raises(NotFoundError) as info:
        Template.get("nope", **CONN)
    assert info.value.request_id == "r"


def test_list_walks_every_page(rsps):
    rsps.add(
        responses.GET,
        BASE,
        json={"templates": [tpl(template_id="a")], "next_page_token": "t2"},
    )
    rsps.add(responses.GET, BASE, json={"templates": [tpl(template_id="b")]})
    ids = [t.template_id for t in Template.list(limit=1, **CONN)]
    assert ids == ["a", "b"]
    assert "page_size=1" in rsps.calls[0].request.url
    assert "page_token=t2" in rsps.calls[1].request.url


def test_list_one_page_at_a_time(rsps):
    rsps.add(responses.GET, BASE, json={"templates": [tpl()], "next_page_token": "t2"})
    pages = Template.list(**CONN)
    assert pages.has_next
    assert [t.template_id for t in pages.next_items()] == ["t-1"]
    assert pages.next_token == "t2"


def test_builds_list_and_get(rsps):
    rsps.add(responses.GET, BASE + "/t-1", json={"template": tpl()})
    template = Template.get("t-1", **CONN)
    build = {
        "build_id": "b-1",
        "template_id": "t-1",
        "status": "TEMPLATE_BUILD_STATUS_FAILED",
        "error": "image not found",
        "created_at": "2026-11-20T12:00:00Z",
        "updated_at": "2026-11-20T12:01:00Z",
    }
    rsps.add(
        responses.GET,
        BASE + "/t-1/builds",
        json={"builds": [build], "next_page_token": ""},
    )
    page = template.builds().next_items()
    assert (page[0].build_id, page[0].status, page[0].error) == (
        "b-1",
        "TEMPLATE_BUILD_STATUS_FAILED",
        "image not found",
    )
    rsps.add(responses.GET, BASE + "/t-1/builds/b-1", json={"build": build})
    assert template.build("b-1").error == "image not found"
    with pytest.raises(SandboxError, match="build_id"):
        template.build(" ")


def test_wait_until_ready_polls_a_building_template(rsps):
    rsps.add(
        responses.GET, BASE + "/t-1", json={"template": tpl("TEMPLATE_STATUS_BUILDING")}
    )
    template = Template.get("t-1", **CONN)
    rsps.replace(responses.GET, BASE + "/t-1", json={"template": tpl()})
    template.wait_until_ready(poll_interval=0.01)
    assert template.status == "TEMPLATE_STATUS_READY"


def test_wait_until_ready_explains_a_failed_build(rsps):
    rsps.add(
        responses.GET, BASE + "/t-1", json={"template": tpl("TEMPLATE_STATUS_FAILED")}
    )
    template = Template.get("t-1", **CONN)

    def failed(build_id, error, updated):
        return {
            "build_id": build_id,
            "template_id": "t-1",
            "status": "TEMPLATE_BUILD_STATUS_FAILED",
            "error": error,
            "updated_at": updated,
        }

    rsps.add(
        responses.GET,
        BASE + "/t-1/builds",
        json={
            "builds": [
                failed("old", "old error", "2026-11-20T10:00:00Z"),
                failed("new", "image not found", "2026-11-20T12:00:00Z"),
            ]
        },
    )
    with pytest.raises(SandboxError, match="failed to build: image not found"):
        template.wait_until_ready()


def test_wait_until_ready_times_out(rsps):
    rsps.add(
        responses.GET, BASE + "/t-1", json={"template": tpl("TEMPLATE_STATUS_BUILDING")}
    )
    template = Template.get("t-1", **CONN)
    with pytest.raises(SandboxError, match="not ready in time"):
        template.wait_until_ready(timeout=0.05, poll_interval=0.01)


def test_sandbox_client_binds_options_for_templates(rsps):
    rsps.add(
        responses.POST,
        BASE,
        json={"template": tpl("TEMPLATE_STATUS_PENDING")},
        status=201,
    )
    template = SandboxClient(**CONN).Template.create(
        name="my-template", source_oci_ref="r/i:v1"
    )
    assert template.template_id == "t-1"


def test_a_ready_templates_name_creates_a_sandbox(rsps):
    rsps.add(responses.GET, BASE + "/t-1", json={"template": tpl()})
    template = Template.get("t-1", **CONN)
    rsps.add(
        responses.POST,
        API + "/v2/sandboxes",
        json={
            "sandbox": {
                "sandbox_id": "sb-1",
                "template": "my-template",
                "state": "SANDBOX_STATE_RUNNING",
                "size_slug": "mars-2vcpu-4gb",
                "created_at": "2026-11-20T12:00:00Z",
            }
        },
        status=201,
    )
    sandbox = Sandbox.create(template=template.name, **CONN)
    assert body_of(rsps)["template"] == "my-template"
    assert sandbox.template == "my-template"
