# pylint: disable=missing-function-docstring,protected-access
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async unit tests for :mod:`pydo.aio.gateway.endpoint`."""

from __future__ import annotations

import asyncio
import importlib.util
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from pydo.aio.gateway import AsyncEndpointsOperations
from pydo.gateway import ACTOR_ID_HEADER, SESSION_ID_HEADER

from .conftest import (
    TEST_BACKING_SESSION_ID,
    TEST_ENDPOINT_ID,
    TEST_ENDPOINT_MCP_URL,
    TEST_GATEWAY_URL,
    TEST_VERSION_MCP_URL,
    AsyncFakeResponse,
    call_result,
    chat_tool_response,
    endpoint_payload,
    endpoint_publish_response,
    endpoint_version_payload,
    jsonrpc_result,
    make_async_parent,
)

_VERSION_ID = f"{TEST_ENDPOINT_ID}.v1"
_HAS_AIO = importlib.util.find_spec("aiohttp") is not None


def _run(coro):
    return asyncio.run(coro)


def _mock_parent(responses=()):
    parent = make_async_parent(list(responses))
    parent.endpoints = MagicMock()
    parent.endpoint_versions = MagicMock()
    return parent


def _ops(parent):
    return AsyncEndpointsOperations(parent, gateway_endpoint=TEST_GATEWAY_URL)


def test_create_delegates_to_generated_operation():
    parent = _mock_parent()
    parent.endpoints.create = AsyncMock(return_value=endpoint_publish_response())

    endpoint = _run(
        _ops(parent).create(
            "support-agent",
            actor_id="actor-123",
            config={"preloadTools": ["exa_web_search@1"]},
            insights={"traces": True},
        )
    )

    parent.endpoints.create.assert_awaited_once()
    assert parent.endpoints.create.await_args.kwargs["body"] == {
        "name": "support-agent",
        "version": {
            "actor_id": "actor-123",
            "policy": {"defaultAction": "ask"},
            "config": {"preloadTools": ["exa_web_search@1"]},
        },
        "insights": {"traces": True},
    }
    assert endpoint.url == TEST_ENDPOINT_MCP_URL
    assert endpoint.version_mcp_url == TEST_VERSION_MCP_URL


def test_endpoint_and_version_tools_use_their_mcp_urls():
    parent = _mock_parent(
        [
            AsyncFakeResponse(200, jsonrpc_result({"tools": []})),
            AsyncFakeResponse(
                200, jsonrpc_result(call_result(structured={"ok": True}))
            ),
        ]
    )
    parent.endpoints.get = AsyncMock(
        return_value={
            "endpoint": endpoint_payload(head_version=endpoint_version_payload())
        }
    )

    async def scenario():
        endpoint = await _ops(parent).get(TEST_ENDPOINT_ID)
        await endpoint.tools.list(include_all=True)
        return await endpoint.head_version.handle_tool_calls(chat_tool_response())

    messages = _run(scenario())

    live, pinned = (call.request for call in parent._client._pipeline.calls)
    assert live.url == TEST_ENDPOINT_MCP_URL
    assert pinned.url == TEST_VERSION_MCP_URL
    for request in (live, pinned):
        assert request.headers[ACTOR_ID_HEADER] == "actor-123"
        assert SESSION_ID_HEADER not in request.headers
    assert messages[0]["role"] == "tool"


def test_endpoint_approval_uses_endpoint_route():
    parent = _mock_parent([AsyncFakeResponse(200, {"status": "approved"})])
    parent.endpoint_versions.get = AsyncMock(
        return_value={"version": endpoint_version_payload(actor_id="")}
    )

    async def scenario():
        version = await _ops(parent).get_version(_VERSION_ID)
        return await version.approve("approval-123")

    result = _run(scenario())

    request = parent._client._pipeline.calls[0].request
    assert request.url == (
        f"{TEST_GATEWAY_URL}/approvals/endpoint/{TEST_ENDPOINT_ID}"
        f"/version/{TEST_BACKING_SESSION_ID}/approval-123"
    )
    assert ACTOR_ID_HEADER not in request.headers
    assert json.loads(request.content) == {"decision": "approve"}
    assert result.status == "approved"


def test_version_lifecycle_delegates_to_generated_operations():
    parent = _mock_parent()
    versions = parent.endpoint_versions
    versions.create = AsyncMock(return_value=endpoint_publish_response(number=2))
    versions.create_promotion = AsyncMock(
        return_value=endpoint_publish_response(number=3, promoted_from=1)
    )
    versions.list = AsyncMock(
        return_value={
            "versions": [endpoint_version_payload(number=3)],
            "next_page_token": "",
        }
    )
    versions.delete = AsyncMock(return_value=None)
    ops = _ops(parent)

    async def scenario():
        created = await ops.create_version(TEST_ENDPOINT_ID, actor_id="actor-123")
        promoted = await ops.promote(TEST_ENDPOINT_ID, _VERSION_ID)
        page = await ops.list_versions(TEST_ENDPOINT_ID)
        await ops.delete_version(_VERSION_ID)
        return created, promoted, page

    created, promoted, page = _run(scenario())

    assert created.version_number == 2
    assert promoted.promoted_from_version_number == 1
    versions.create_promotion.assert_awaited_once_with(
        TEST_ENDPOINT_ID, body={"version_id": _VERSION_ID}
    )
    versions.list.assert_awaited_once_with(TEST_ENDPOINT_ID)
    assert [version.version_number for version in page.versions] == [3]
    versions.delete.assert_awaited_once_with(_VERSION_ID)


def test_endpoint_lifecycle_delegates_to_generated_operations():
    parent = _mock_parent()
    endpoints = parent.endpoints
    endpoints.list = AsyncMock(
        return_value={"endpoints": [endpoint_payload()], "next_page_token": "n"}
    )
    endpoints.list_search = AsyncMock(
        return_value={"endpoints": [], "next_page_token": ""}
    )
    endpoints.patch = AsyncMock(
        return_value={"endpoint": endpoint_payload(name="renamed")}
    )
    endpoints.delete = AsyncMock(return_value=None)
    ops = _ops(parent)

    async def scenario():
        page = await ops.list(name="support-agent")
        found = await ops.search("support", actor_id="actor-123")
        renamed = await ops.update(TEST_ENDPOINT_ID, name="renamed")
        await ops.delete(TEST_ENDPOINT_ID)
        return page, found, renamed

    page, found, renamed = _run(scenario())

    endpoints.list.assert_awaited_once_with(name="support-agent")
    assert page.next_page_token == "n"
    assert page.endpoints[0].head_version is None
    endpoints.list_search.assert_awaited_once_with(
        query="support", actor_id="actor-123"
    )
    assert found.endpoints == []
    endpoints.patch.assert_awaited_once_with(TEST_ENDPOINT_ID, body={"name": "renamed"})
    assert renamed.name == "renamed"
    endpoints.delete.assert_awaited_once_with(TEST_ENDPOINT_ID)


def test_list_reports_default_endpoint():
    parent = _mock_parent()
    parent.endpoints.list = AsyncMock(
        return_value={
            "endpoints": [
                endpoint_payload(name="default", is_default=True),
                endpoint_payload(),
            ],
            "next_page_token": "",
        }
    )

    page = _run(_ops(parent).list())

    assert [endpoint.is_default for endpoint in page.endpoints] == [True, False]


def test_missing_generated_operations_raise_clear_error():
    ops = AsyncEndpointsOperations(
        SimpleNamespace(_client=MagicMock()), gateway_endpoint=TEST_GATEWAY_URL
    )
    with pytest.raises(RuntimeError, match="upgrade pydo"):
        _run(ops.list())


@pytest.mark.skipif(not _HAS_AIO, reason="aiohttp extra not installed")
def test_async_action_gateway_client_exposes_endpoints():
    # pylint: disable-next=import-outside-toplevel
    from pydo.action_gateway.aio import ActionGatewayClient

    client = ActionGatewayClient(token="dummy")
    assert client.endpoints is client.gateway.endpoints
    assert client.endpoints_api is not client.endpoints
