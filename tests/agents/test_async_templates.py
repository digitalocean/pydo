# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Unit tests for :mod:`pydo.aio.agents.custom_templates`."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from pydo.aio.agents import AsyncAgentsResources
from pydo.agents import TemplateBuildStatus, TemplateStatus


class _FakeAsyncResponse:
    def __init__(self, status_code: int, body: Any = None):
        self.status_code = status_code
        if isinstance(body, (dict, list)):
            self._body_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            self._body_bytes = body.encode("utf-8")
        elif isinstance(body, bytes):
            self._body_bytes = body
        else:
            self._body_bytes = b""

    async def read(self) -> bytes:
        return self._body_bytes

    def text(self) -> str:
        return self._body_bytes.decode("utf-8")

    def body(self) -> bytes:
        return self._body_bytes


class _FakeAsyncPipeline:
    def __init__(self, responses: List[_FakeAsyncResponse]):
        self._responses = list(responses)
        self.calls: List[Any] = []

    async def run(self, request, *, stream=False, **kwargs):
        self.calls.append(SimpleNamespace(request=request, stream=stream))
        return SimpleNamespace(http_response=self._responses.pop(0))


def _make_async_resources(responses: List[_FakeAsyncResponse]) -> AsyncAgentsResources:
    parent = MagicMock()
    parent._client = MagicMock()
    parent._client._pipeline = _FakeAsyncPipeline(responses)
    return AsyncAgentsResources(
        parent, agents_endpoint="https://api.stage2.digitalocean.com"
    )


def _path(url: str) -> str:
    return url.split("?", 1)[0]


@pytest.mark.asyncio
async def test_async_templates_crud_and_builds():
    resources = _make_async_resources(
        [
            _FakeAsyncResponse(
                200,
                {
                    "templates": [
                        {
                            "template_id": "tmpl-1",
                            "name": "demo",
                            "status": TemplateStatus.READY,
                        }
                    ],
                    "next_page_token": "",
                },
            ),
            _FakeAsyncResponse(
                201,
                {
                    "template": {
                        "template_id": "tmpl-2",
                        "name": "new",
                        "status": TemplateStatus.PENDING,
                    }
                },
            ),
            _FakeAsyncResponse(
                200,
                {
                    "template": {
                        "template_id": "tmpl-2",
                        "status": TemplateStatus.PENDING,
                    }
                },
            ),
            _FakeAsyncResponse(
                200,
                {"template_id": "tmpl-2", "deleted": True},
            ),
            _FakeAsyncResponse(
                200,
                {
                    "builds": [
                        {
                            "build_id": "bld-1",
                            "status": TemplateBuildStatus.SUCCEEDED,
                        }
                    ]
                },
            ),
            _FakeAsyncResponse(
                200,
                {
                    "build": {
                        "build_id": "bld-1",
                        "status": TemplateBuildStatus.SUCCEEDED,
                    }
                },
            ),
        ]
    )

    listed = await resources.templates.list(page_size=5)
    assert listed.templates[0].template_id == "tmpl-1"

    created = await resources.templates.create(
        {
            "name": "new",
            "base_template": "coding-base",
            "source_oci_ref": "registry.example/app:1",
        }
    )
    assert created.template.template_id == "tmpl-2"

    updated = await resources.templates.update(
        "tmpl-2", {"source_oci_ref": "registry.example/app:2"}
    )
    assert updated.template.template_id == "tmpl-2"

    deleted = await resources.templates.delete("tmpl-2")
    assert deleted.deleted is True

    builds = await resources.templates.list_builds("tmpl-2")
    assert builds.builds[0].build_id == "bld-1"

    build = await resources.templates.get_build("tmpl-2", "bld-1")
    assert build.build.build_id == "bld-1"

    pipeline = resources._proxy._original._pipeline
    methods = [c.request.method for c in pipeline.calls]
    paths = [_path(c.request.url) for c in pipeline.calls]
    assert methods == ["GET", "POST", "PUT", "DELETE", "GET", "GET"]
    assert paths[0].endswith("/v2/agents/templates")
    assert paths[1].endswith("/v2/agents/templates")
    assert paths[2].endswith("/v2/agents/templates/tmpl-2")
    assert paths[3].endswith("/v2/agents/templates/tmpl-2")
    assert paths[4].endswith("/v2/agents/templates/tmpl-2/builds")
    assert paths[5].endswith("/v2/agents/templates/tmpl-2/builds/bld-1")
    assert not hasattr(resources.templates, "get_build_logs")
