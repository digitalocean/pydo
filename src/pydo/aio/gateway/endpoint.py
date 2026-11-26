# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
# pylint: disable=duplicate-code
"""Async Action Gateway endpoints (mirror of :mod:`pydo.gateway.endpoint`)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from pydo.custom_extensions import _BaseURLProxy
from pydo.gateway.endpoint import (
    EndpointFields,
    EndpointPage,
    EndpointVersionFields,
    EndpointVersionPage,
    _create_body,
    _mcp_url,
    _page_items,
    _publish_parts,
    _query,
    _require_object,
    _require_text,
    _update_body,
    _version_spec,
)
from pydo.gateway.providers import BaseProvider, default_provider
from pydo.gateway.transport import resolve_gateway_base_url

from .custom_operations import (
    AsyncCodeOperations,
    AsyncEndpointMCPTransport,
    AsyncToolsOperations,
    async_execute_tool_calls,
)


class _AsyncToolSurface:
    def __init__(
        self, tools: AsyncToolsOperations, code: AsyncCodeOperations, provider: Any
    ):
        self.tools = tools
        self.code = code
        self.provider = provider
        self._transport = tools._transport

    async def handle_tool_calls(
        self,
        response: Any,
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        """Execute tool calls from an inference response against this target."""
        calls = self.provider.extract_tool_calls(response)
        if not calls:
            return []
        results = await async_execute_tool_calls(calls, self.tools, rationale=rationale)
        return self.provider.format_tool_results(calls, results)

    async def execute_tool_calls(
        self,
        calls: Sequence[Any],
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        """Execute pre-extracted tool calls; return raw outputs."""
        return await async_execute_tool_calls(calls, self.tools, rationale=rationale)

    async def approve(self, approval_id: str) -> Any:
        """Approve a pending tool invocation made through this target."""
        return await self._transport.decide_approval(approval_id, "approve")

    async def deny(self, approval_id: str) -> Any:
        """Deny a pending tool invocation made through this target."""
        return await self._transport.decide_approval(approval_id, "deny")


class AsyncEndpointVersion(EndpointVersionFields, _AsyncToolSurface):
    """Async twin of :class:`pydo.gateway.endpoint.EndpointVersion`."""

    def __init__(
        self,
        raw: Dict[str, Any],
        *,
        mcp_url: str,
        tools: AsyncToolsOperations,
        code: AsyncCodeOperations,
        provider: BaseProvider,
    ):
        EndpointVersionFields.__init__(self, raw, mcp_url=mcp_url)
        _AsyncToolSurface.__init__(self, tools, code, provider)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AsyncEndpointVersion id={self.id!r}>"


class AsyncEndpoint(EndpointFields, _AsyncToolSurface):
    """Async twin of :class:`pydo.gateway.endpoint.Endpoint`."""

    head_version: Optional[AsyncEndpointVersion]

    def __init__(
        self,
        raw: Dict[str, Any],
        *,
        mcp_url: str,
        head_version: Optional[AsyncEndpointVersion],
        tools: AsyncToolsOperations,
        code: AsyncCodeOperations,
        provider: BaseProvider,
    ):
        EndpointFields.__init__(self, raw, mcp_url=mcp_url)
        _AsyncToolSurface.__init__(self, tools, code, provider)
        self.head_version = head_version

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AsyncEndpoint id={self.id!r} name={self.name!r}>"


class AsyncEndpointsOperations:
    """Async twin of :class:`pydo.gateway.endpoint.EndpointsOperations`."""

    def __init__(
        self,
        parent_client: Any,
        *,
        gateway_endpoint: Optional[str] = None,
        provider: Optional[BaseProvider] = None,
    ):
        self._parent = parent_client
        self._endpoints_api = getattr(parent_client, "endpoints", None)
        self._versions_api = getattr(parent_client, "endpoint_versions", None)
        self._gateway_base_url = resolve_gateway_base_url(gateway_endpoint)
        self._provider = provider or default_provider()

    def _generated(self, api: Any) -> Any:
        if api is None:
            raise RuntimeError(
                "this pydo build has no generated Action Gateway endpoint "
                "operations; upgrade pydo"
            )
        return api

    def _bind(
        self, mcp_url: str, actor_id: Optional[str]
    ) -> Tuple[AsyncToolsOperations, AsyncCodeOperations]:
        transport = AsyncEndpointMCPTransport(
            _BaseURLProxy(self._parent._client, self._gateway_base_url),
            mcp_url=mcp_url,
            actor_id=actor_id,
        )
        return (
            AsyncToolsOperations(transport, self._provider),
            AsyncCodeOperations(transport),
        )

    def _version(
        self, raw: Dict[str, Any], mcp_url: Optional[str] = None
    ) -> AsyncEndpointVersion:
        url = _mcp_url(raw, mcp_url, "endpoint version")
        tools, code = self._bind(url, raw.get("actor_id"))
        return AsyncEndpointVersion(
            raw, mcp_url=url, tools=tools, code=code, provider=self._provider
        )

    def _endpoint(
        self,
        raw: Dict[str, Any],
        mcp_url: Optional[str] = None,
        head_version: Optional[AsyncEndpointVersion] = None,
    ) -> AsyncEndpoint:
        url = _mcp_url(raw, mcp_url, "endpoint")
        if head_version is None and isinstance(raw.get("head_version"), dict):
            head_version = self._version(raw["head_version"])
        tools, code = self._bind(url, raw.get("actor_id"))
        return AsyncEndpoint(
            raw,
            mcp_url=url,
            head_version=head_version,
            tools=tools,
            code=code,
            provider=self._provider,
        )

    def _published(self, payload: Any) -> AsyncEndpoint:
        endpoint, version, mcp_url, version_mcp_url = _publish_parts(payload)
        return self._endpoint(
            endpoint, mcp_url, head_version=self._version(version, version_mcp_url)
        )

    # -- endpoints ----------------------------------------------------------

    async def create(
        self,
        name: str,
        *,
        actor_id: Optional[str] = None,
        permissions: Optional[Dict[str, Any]] = None,
        tools: Optional[Sequence[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        vpc_uuid: Optional[str] = None,
        insights: Optional[Dict[str, Any]] = None,
    ) -> AsyncEndpoint:
        """Create an endpoint and its first version; see the sync docstring."""
        version = _version_spec(
            actor_id=actor_id,
            permissions=permissions,
            tools=tools,
            config=config,
            vpc_uuid=vpc_uuid,
        )
        body = _create_body(name, version, insights)
        payload = await self._generated(self._endpoints_api).create(body=body)
        return self._published(payload)

    async def get(self, endpoint_id: str) -> AsyncEndpoint:
        """Retrieve an endpoint and its live head version."""
        payload = await self._generated(self._endpoints_api).get(
            _require_text(endpoint_id, "endpoint_id")
        )
        return self._endpoint(_require_object(payload, "endpoint"))

    async def list(
        self,
        *,
        name: Optional[str] = None,
        actor_id: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> EndpointPage:
        """List endpoints, newest first, one page at a time."""
        payload = await self._generated(self._endpoints_api).list(
            **_query(
                name=name,
                actor_id=actor_id,
                page_size=page_size,
                page_token=page_token,
            )
        )
        items, token = _page_items(payload, "endpoints")
        return EndpointPage([self._endpoint(item) for item in items], token)

    async def search(
        self,
        query: str,
        *,
        actor_id: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> EndpointPage:
        """Search endpoints by name, ID, or actor, ranked by match quality."""
        payload = await self._generated(self._endpoints_api).list_search(
            **_query(
                query=_require_text(query, "query"),
                actor_id=actor_id,
                page_size=page_size,
                page_token=page_token,
            )
        )
        items, token = _page_items(payload, "endpoints")
        return EndpointPage([self._endpoint(item) for item in items], token)

    async def update(
        self,
        endpoint_id: str,
        *,
        name: Optional[str] = None,
        insights: Optional[Dict[str, Any]] = None,
    ) -> AsyncEndpoint:
        """Rename an endpoint, change its Insights consent, or both."""
        payload = await self._generated(self._endpoints_api).patch(
            _require_text(endpoint_id, "endpoint_id"),
            body=_update_body(name, insights),
        )
        return self._endpoint(_require_object(payload, "endpoint"))

    async def delete(self, endpoint_id: str) -> None:
        """Delete an endpoint and all of its versions."""
        await self._generated(self._endpoints_api).delete(
            _require_text(endpoint_id, "endpoint_id")
        )

    # -- versions -----------------------------------------------------------

    async def create_version(
        self,
        endpoint_id: str,
        *,
        actor_id: Optional[str] = None,
        permissions: Optional[Dict[str, Any]] = None,
        tools: Optional[Sequence[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        vpc_uuid: Optional[str] = None,
    ) -> AsyncEndpointVersion:
        """Publish a new immutable version, which becomes the endpoint's head."""
        body = _version_spec(
            actor_id=actor_id,
            permissions=permissions,
            tools=tools,
            config=config,
            vpc_uuid=vpc_uuid,
        )
        payload = await self._generated(self._versions_api).create(
            _require_text(endpoint_id, "endpoint_id"), body=body
        )
        return self._published(payload).head_version

    async def list_versions(
        self,
        endpoint_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> EndpointVersionPage:
        """List an endpoint's live versions, newest first."""
        payload = await self._generated(self._versions_api).list(
            _require_text(endpoint_id, "endpoint_id"),
            **_query(page_size=page_size, page_token=page_token),
        )
        items, token = _page_items(payload, "versions")
        return EndpointVersionPage([self._version(item) for item in items], token)

    async def get_version(self, version_id: str) -> AsyncEndpointVersion:
        """Retrieve a version by its ID (``<endpoint_id>.v<number>``)."""
        payload = await self._generated(self._versions_api).get(
            _require_text(version_id, "version_id")
        )
        return self._version(_require_object(payload, "version"))

    async def delete_version(self, version_id: str) -> None:
        """Delete a version. Deleting the head makes the next-highest the head."""
        await self._generated(self._versions_api).delete(
            _require_text(version_id, "version_id")
        )

    async def promote(self, endpoint_id: str, version_id: str) -> AsyncEndpointVersion:
        """Copy a live version into a new head version."""
        payload = await self._generated(self._versions_api).create_promotion(
            _require_text(endpoint_id, "endpoint_id"),
            body={"version_id": _require_text(version_id, "version_id")},
        )
        return self._published(payload).head_version


__all__ = [
    "AsyncEndpoint",
    "AsyncEndpointVersion",
    "AsyncEndpointsOperations",
]
