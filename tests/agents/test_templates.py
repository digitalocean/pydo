# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :mod:`pydo.agents.custom_templates`."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import HttpResponseError

from pydo.agents import AgentsResources, TemplateBuildStatus, TemplateStatus


class _FakeResponse:
    def __init__(self, status_code: int, body: Any = None):
        self.status_code = status_code
        self.reason = None
        if isinstance(body, (dict, list)):
            self._body_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            self._body_bytes = body.encode("utf-8")
        elif isinstance(body, bytes):
            self._body_bytes = body
        else:
            self._body_bytes = b""

    def text(self) -> str:
        return self._body_bytes.decode("utf-8")

    def body(self) -> bytes:
        return self._body_bytes

    def read(self) -> bytes:
        return self._body_bytes

    def close(self) -> None:
        pass


def _path(url: str) -> str:
    return url.split("?", 1)[0]


class _FakePipeline:
    def __init__(self, responses: List[_FakeResponse]):
        self._responses = list(responses)
        self.calls: List[Any] = []

    def run(self, request, *, stream=False, **kwargs):
        self.calls.append(SimpleNamespace(request=request, stream=stream))
        response = self._responses.pop(0)
        return SimpleNamespace(http_response=response)


def _make_resources(responses: List[_FakeResponse]) -> AgentsResources:
    parent = MagicMock()
    parent._client = MagicMock()
    parent._client._pipeline = _FakePipeline(responses)
    return AgentsResources(
        parent, agents_endpoint="https://api.stage2.digitalocean.com"
    )


def _last_call(resources: AgentsResources):
    return resources._proxy._original._pipeline.calls[-1]


def test_list_templates_pagination():
    body = {
        "templates": [
            {
                "template_id": "tmpl-1",
                "name": "my-base",
                "status": TemplateStatus.READY,
            }
        ],
        "next_page_token": "next",
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.templates.list(page_size=25, page_token="tok")

    call = _last_call(resources)
    assert call.request.method == "GET"
    assert _path(call.request.url).endswith("/v2/agents/templates")
    assert "page_size=25" in call.request.url
    assert "page_token=tok" in call.request.url
    assert resp.templates[0].template_id == "tmpl-1"
    assert resp.next_page_token == "next"


def test_get_template():
    body = {
        "template": {
            "template_id": "tmpl-1",
            "name": "demo",
            "status": TemplateStatus.BUILDING,
        }
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.templates.get("tmpl-1")

    call = _last_call(resources)
    assert call.request.method == "GET"
    assert _path(call.request.url).endswith("/v2/agents/templates/tmpl-1")
    assert resp.template.name == "demo"


def test_create_template():
    body = {
        "template": {
            "template_id": "tmpl-new",
            "name": "custom",
            "status": TemplateStatus.PENDING,
        }
    }
    resources = _make_resources([_FakeResponse(201, body)])

    resp = resources.templates.create(
        {
            "name": "custom",
            "base_template": "coding-base",
            "source_oci_ref": "registry.example/app:1",
        }
    )

    call = _last_call(resources)
    assert call.request.method == "POST"
    assert _path(call.request.url).endswith("/v2/agents/templates")
    assert call.request.headers.get("Content-Type") == "application/json"
    assert resp.template.template_id == "tmpl-new"


def test_create_template_rejects_empty_body():
    resources = _make_resources([])
    with pytest.raises(ValueError, match="non-empty dict"):
        resources.templates.create({})


def test_update_template():
    body = {
        "template": {
            "template_id": "tmpl-1",
            "status": TemplateStatus.PENDING,
        }
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.templates.update(
        "tmpl-1",
        {"source_oci_ref": "registry.example/app:2"},
    )

    call = _last_call(resources)
    assert call.request.method == "PUT"
    assert _path(call.request.url).endswith("/v2/agents/templates/tmpl-1")
    assert resp.template.template_id == "tmpl-1"


def test_update_template_rejects_empty_body():
    resources = _make_resources([])
    with pytest.raises(ValueError, match="non-empty dict"):
        resources.templates.update("tmpl-1", {})


def test_delete_template():
    body = {"template_id": "tmpl-1", "deleted": True}
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.templates.delete("tmpl-1")

    call = _last_call(resources)
    assert call.request.method == "DELETE"
    assert _path(call.request.url).endswith("/v2/agents/templates/tmpl-1")
    assert resp.deleted is True


def test_list_builds():
    body = {
        "builds": [
            {
                "build_id": "bld-1",
                "template_id": "tmpl-1",
                "status": TemplateBuildStatus.SUCCEEDED,
            }
        ],
        "next_page_token": "",
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.templates.list_builds("tmpl-1", page_size=10, page_token="tok")

    call = _last_call(resources)
    assert call.request.method == "GET"
    assert _path(call.request.url).endswith("/v2/agents/templates/tmpl-1/builds")
    assert "page_size=10" in call.request.url
    assert resp.builds[0].build_id == "bld-1"


def test_get_build():
    body = {
        "build": {
            "build_id": "bld-1",
            "template_id": "tmpl-1",
            "status": TemplateBuildStatus.FAILED,
            "error": "boom",
        }
    }
    resources = _make_resources([_FakeResponse(200, body)])

    resp = resources.templates.get_build("tmpl-1", "bld-1")

    call = _last_call(resources)
    assert call.request.method == "GET"
    assert _path(call.request.url).endswith("/v2/agents/templates/tmpl-1/builds/bld-1")
    assert resp.build.error == "boom"


def test_no_build_logs_method():
    """Build-logs signed-URL endpoint is intentionally not exposed."""
    resources = _make_resources([])
    assert not hasattr(resources.templates, "get_build_logs")
    assert not hasattr(resources.templates, "get_logs")


def test_get_template_not_found_raises():
    resources = _make_resources(
        [_FakeResponse(404, {"id": "not_found", "message": "missing"})]
    )
    with pytest.raises(HttpResponseError):
        resources.templates.get("missing")
