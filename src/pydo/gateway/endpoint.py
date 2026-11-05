# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
# pylint: disable=duplicate-code
"""Action Gateway endpoints — named MCP targets with immutable versions.

An endpoint's ``mcp_url`` always serves its highest-numbered live version, so
publishing or promoting a version changes what connected agents get without
changing their URL. Each version's own ``mcp_url`` (``version_mcp_url`` in
create responses) stays pinned to that version for its lifetime. Endpoints
replace sessions: a session is equivalent to a single endpoint version.
"""

from __future__ import annotations

from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from pydo.custom_extensions import _BaseURLProxy

from .custom_models import GatewayProtocolError
from .custom_operations import CodeOperations, ToolsOperations
from .providers import BaseProvider, default_provider, execute_tool_calls
from .session import normalize_permissions
from .transport import EndpointMCPTransport, resolve_gateway_base_url


def _require_text(value: Any, field: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{field} is required")
    return str(value).strip()


def _version_spec(
    *,
    actor_id: Optional[str],
    permissions: Optional[Dict[str, Any]],
    tools: Optional[Sequence[str]],
    config: Optional[Dict[str, Any]],
    vpc_uuid: Optional[str],
) -> Dict[str, Any]:
    spec: Dict[str, Any] = {"policy": normalize_permissions(permissions)}
    if actor_id is not None and str(actor_id).strip():
        spec["actor_id"] = str(actor_id).strip()
    if tools is not None:
        if isinstance(tools, (str, bytes)):
            raise TypeError("tools must be a sequence of tool references")
        spec["tools"] = list(tools)
    if config is not None:
        if not isinstance(config, dict):
            raise TypeError("config must be a dict")
        spec["config"] = config
    if vpc_uuid is not None:
        spec["network"] = {"vpcUuid": _require_text(vpc_uuid, "vpc_uuid")}
    return spec


def _insights(insights: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(insights, dict):
        raise TypeError("insights must be a dict such as {'logs': True}")
    return dict(insights)


def _create_body(
    name: str, version: Dict[str, Any], insights: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"name": _require_text(name, "name"), "version": version}
    if insights is not None:
        body["insights"] = _insights(insights)
    return body


def _update_body(
    name: Optional[str], insights: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if name is not None:
        body["name"] = _require_text(name, "name")
    if insights is not None:
        body["insights"] = _insights(insights)
    if not body:
        raise ValueError("update requires name, insights, or both")
    return body


def _query(**params: Any) -> Dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


def _require_object(payload: Any, key: str) -> Dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get(key), dict):
        raise GatewayProtocolError(f"endpoint response missing {key}: {payload!r}")
    return payload[key]


def _publish_parts(
    payload: Any,
) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[str], Optional[str]]:
    endpoint = _require_object(payload, "endpoint")
    version = _require_object(payload, "version")
    return endpoint, version, payload.get("mcp_url"), payload.get("version_mcp_url")


def _page_items(payload: Any, key: str) -> Tuple[List[Dict[str, Any]], str]:
    if not isinstance(payload, dict):
        raise GatewayProtocolError(f"unexpected endpoint list response: {payload!r}")
    items = payload.get(key) or []
    return [item for item in items if isinstance(item, dict)], (
        payload.get("next_page_token") or ""
    )


def _mcp_url(raw: Dict[str, Any], fallback: Optional[str], kind: str) -> str:
    url = raw.get("mcp_url") or fallback
    if not url:
        raise GatewayProtocolError(f"{kind} response missing mcp_url: {raw!r}")
    return url


class EndpointPage(NamedTuple):
    """One page of endpoints. An empty ``next_page_token`` marks the last page."""

    endpoints: List[Any]
    next_page_token: str


class EndpointVersionPage(NamedTuple):
    """One page of versions, newest first. An empty token marks the last page."""

    versions: List[Any]
    next_page_token: str


class EndpointVersionFields:
    """Fields of an immutable endpoint version, as returned by the API."""

    def __init__(self, raw: Dict[str, Any], *, mcp_url: str):
        self.raw = raw
        self.id: str = raw.get("id") or ""
        self.endpoint_id: str = raw.get("endpoint_id") or ""
        self.version_number: Optional[int] = raw.get("version_number")
        self.promoted_from_version_number: Optional[int] = raw.get(
            "promoted_from_version_number"
        )
        self.actor_id: Optional[str] = raw.get("actor_id") or None
        self.policy: Optional[Dict[str, Any]] = raw.get("policy")
        self.tool_selection: Optional[Dict[str, Any]] = raw.get("tools")
        self.config: Optional[Dict[str, Any]] = raw.get("config")
        self.network: Optional[Dict[str, Any]] = raw.get("network")
        self.created_at: Optional[str] = raw.get("created_at")
        self.mcp_url = mcp_url

    @property
    def url(self) -> str:
        """MCP URL pinned to this version for external MCP clients."""
        return self.mcp_url


class EndpointFields:
    """Fields of an endpoint, as returned by the API."""

    head_version: Optional[EndpointVersionFields]

    def __init__(self, raw: Dict[str, Any], *, mcp_url: str):
        self.raw = raw
        self.id: str = raw.get("id") or ""
        self.name: str = raw.get("name") or ""
        self.actor_id: Optional[str] = raw.get("actor_id") or None
        self.is_default: bool = bool(raw.get("is_default", False))
        self.insights: Optional[Dict[str, Any]] = raw.get("insights")
        self.created_at: Optional[str] = raw.get("created_at")
        self.updated_at: Optional[str] = raw.get("updated_at")
        self.mcp_url = mcp_url

    @property
    def url(self) -> str:
        """MCP URL that follows the head version, for external MCP clients."""
        return self.mcp_url

    @property
    def version_mcp_url(self) -> Optional[str]:
        """MCP URL pinned to the current head version, if one is live."""
        return self.head_version.mcp_url if self.head_version else None


class _ToolSurface:
    def __init__(self, tools: ToolsOperations, code: CodeOperations, provider: Any):
        self.tools = tools
        self.code = code
        self.provider = provider
        self._transport = tools._transport

    def handle_tool_calls(
        self,
        response: Any,
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        """Execute tool calls from an inference response against this target."""
        calls = self.provider.extract_tool_calls(response)
        if not calls:
            return []
        results = execute_tool_calls(calls, self.tools, rationale=rationale)
        return self.provider.format_tool_results(calls, results)

    def execute_tool_calls(
        self,
        calls: Sequence[Any],
        *,
        rationale: Optional[str] = None,
    ) -> List[Any]:
        """Execute pre-extracted tool calls; return raw outputs."""
        return execute_tool_calls(calls, self.tools, rationale=rationale)

    def approve(self, approval_id: str) -> Any:
        """Approve a pending tool invocation made through this target."""
        return self._transport.decide_approval(approval_id, "approve")

    def deny(self, approval_id: str) -> Any:
        """Deny a pending tool invocation made through this target."""
        return self._transport.decide_approval(approval_id, "deny")


class EndpointVersion(EndpointVersionFields, _ToolSurface):
    """An immutable endpoint version, connected through its pinned MCP URL.

    ``tools``, ``code``, and ``handle_tool_calls`` always run against this
    version, even after a newer version becomes the endpoint's head.
    """

    def __init__(
        self,
        raw: Dict[str, Any],
        *,
        mcp_url: str,
        tools: ToolsOperations,
        code: CodeOperations,
        provider: BaseProvider,
    ):
        EndpointVersionFields.__init__(self, raw, mcp_url=mcp_url)
        _ToolSurface.__init__(self, tools, code, provider)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<EndpointVersion id={self.id!r}>"


class Endpoint(EndpointFields, _ToolSurface):
    """An endpoint, connected through the MCP URL that follows its head version.

    ``tools``, ``code``, and ``handle_tool_calls`` run against whichever
    version is the head when each request arrives. Use :attr:`head_version`
    (or :meth:`EndpointsOperations.get_version`) to pin a version instead.
    """

    head_version: Optional[EndpointVersion]

    def __init__(
        self,
        raw: Dict[str, Any],
        *,
        mcp_url: str,
        head_version: Optional[EndpointVersion],
        tools: ToolsOperations,
        code: CodeOperations,
        provider: BaseProvider,
    ):
        EndpointFields.__init__(self, raw, mcp_url=mcp_url)
        _ToolSurface.__init__(self, tools, code, provider)
        self.head_version = head_version

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Endpoint id={self.id!r} name={self.name!r}>"


class EndpointsOperations:
    """Manage endpoints and versions through the generated Action Gateway operations."""

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
    ) -> Tuple[ToolsOperations, CodeOperations]:
        transport = EndpointMCPTransport(
            _BaseURLProxy(self._parent._client, self._gateway_base_url),
            mcp_url=mcp_url,
            actor_id=actor_id,
        )
        return ToolsOperations(transport, self._provider), CodeOperations(transport)

    def _version(
        self, raw: Dict[str, Any], mcp_url: Optional[str] = None
    ) -> EndpointVersion:
        url = _mcp_url(raw, mcp_url, "endpoint version")
        tools, code = self._bind(url, raw.get("actor_id"))
        return EndpointVersion(
            raw, mcp_url=url, tools=tools, code=code, provider=self._provider
        )

    def _endpoint(
        self,
        raw: Dict[str, Any],
        mcp_url: Optional[str] = None,
        head_version: Optional[EndpointVersion] = None,
    ) -> Endpoint:
        url = _mcp_url(raw, mcp_url, "endpoint")
        if head_version is None and isinstance(raw.get("head_version"), dict):
            head_version = self._version(raw["head_version"])
        tools, code = self._bind(url, raw.get("actor_id"))
        return Endpoint(
            raw,
            mcp_url=url,
            head_version=head_version,
            tools=tools,
            code=code,
            provider=self._provider,
        )

    def _published(self, payload: Any) -> Endpoint:
        endpoint, version, mcp_url, version_mcp_url = _publish_parts(payload)
        return self._endpoint(
            endpoint, mcp_url, head_version=self._version(version, version_mcp_url)
        )

    # -- endpoints ----------------------------------------------------------

    def create(
        self,
        name: str,
        *,
        actor_id: Optional[str] = None,
        permissions: Optional[Dict[str, Any]] = None,
        tools: Optional[Sequence[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        vpc_uuid: Optional[str] = None,
        insights: Optional[Dict[str, Any]] = None,
    ) -> Endpoint:
        """Create an endpoint and its first version.

        :param name: Endpoint name, unique within the team
            (``[A-Za-z0-9._-]``, 1–64 characters).
        :param actor_id: Optional actor whose connections tool calls use. It
            cannot change: every later version must use the same actor.
        :param permissions: Optional policy, as for sessions. When omitted,
            defaults to ``{"defaultAction": "ask"}``.
        :param tools: Optional tool or version-pinned toolbelt references.
            Omit for all tools; pass an empty sequence for no tools.
        :param config: Optional version configuration, such as
            ``preloadTools``.
        :param vpc_uuid: Optional VPC to bind the version to.
        :param insights: Optional Insights consent for the endpoint and all
            its versions, such as ``{"logs": True, "traces": False}``.
        :returns: The endpoint, with the new version as ``head_version``.
        """
        version = _version_spec(
            actor_id=actor_id,
            permissions=permissions,
            tools=tools,
            config=config,
            vpc_uuid=vpc_uuid,
        )
        body = _create_body(name, version, insights)
        return self._published(self._generated(self._endpoints_api).create(body=body))

    def get(self, endpoint_id: str) -> Endpoint:
        """Retrieve an endpoint and its live head version."""
        payload = self._generated(self._endpoints_api).get(
            _require_text(endpoint_id, "endpoint_id")
        )
        return self._endpoint(_require_object(payload, "endpoint"))

    def list(
        self,
        *,
        name: Optional[str] = None,
        actor_id: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> EndpointPage:
        """List endpoints, newest first, one page at a time."""
        payload = self._generated(self._endpoints_api).list(
            **_query(
                name=name,
                actor_id=actor_id,
                page_size=page_size,
                page_token=page_token,
            )
        )
        items, token = _page_items(payload, "endpoints")
        return EndpointPage([self._endpoint(item) for item in items], token)

    def search(
        self,
        query: str,
        *,
        actor_id: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> EndpointPage:
        """Search endpoints by name, ID, or actor, ranked by match quality."""
        payload = self._generated(self._endpoints_api).list_search(
            **_query(
                query=_require_text(query, "query"),
                actor_id=actor_id,
                page_size=page_size,
                page_token=page_token,
            )
        )
        items, token = _page_items(payload, "endpoints")
        return EndpointPage([self._endpoint(item) for item in items], token)

    def update(
        self,
        endpoint_id: str,
        *,
        name: Optional[str] = None,
        insights: Optional[Dict[str, Any]] = None,
    ) -> Endpoint:
        """Rename an endpoint, change its Insights consent, or both.

        An Insights signal that is omitted keeps its stored value.
        """
        payload = self._generated(self._endpoints_api).patch(
            _require_text(endpoint_id, "endpoint_id"),
            body=_update_body(name, insights),
        )
        return self._endpoint(_require_object(payload, "endpoint"))

    def delete(self, endpoint_id: str) -> None:
        """Delete an endpoint and all of its versions."""
        self._generated(self._endpoints_api).delete(
            _require_text(endpoint_id, "endpoint_id")
        )

    # -- versions -----------------------------------------------------------

    def create_version(
        self,
        endpoint_id: str,
        *,
        actor_id: Optional[str] = None,
        permissions: Optional[Dict[str, Any]] = None,
        tools: Optional[Sequence[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        vpc_uuid: Optional[str] = None,
    ) -> EndpointVersion:
        """Publish a new immutable version, which becomes the endpoint's head.

        Takes the same version options as :meth:`create`. ``actor_id`` must
        equal the endpoint's actor, or be omitted for an endpoint without one.
        """
        body = _version_spec(
            actor_id=actor_id,
            permissions=permissions,
            tools=tools,
            config=config,
            vpc_uuid=vpc_uuid,
        )
        payload = self._generated(self._versions_api).create(
            _require_text(endpoint_id, "endpoint_id"), body=body
        )
        return self._published(payload).head_version

    def list_versions(
        self,
        endpoint_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> EndpointVersionPage:
        """List an endpoint's live versions, newest first."""
        payload = self._generated(self._versions_api).list(
            _require_text(endpoint_id, "endpoint_id"),
            **_query(page_size=page_size, page_token=page_token),
        )
        items, token = _page_items(payload, "versions")
        return EndpointVersionPage([self._version(item) for item in items], token)

    def get_version(self, version_id: str) -> EndpointVersion:
        """Retrieve a version by its ID (``<endpoint_id>.v<number>``)."""
        payload = self._generated(self._versions_api).get(
            _require_text(version_id, "version_id")
        )
        return self._version(_require_object(payload, "version"))

    def delete_version(self, version_id: str) -> None:
        """Delete a version. Deleting the head makes the next-highest the head."""
        self._generated(self._versions_api).delete(
            _require_text(version_id, "version_id")
        )

    def promote(self, endpoint_id: str, version_id: str) -> EndpointVersion:
        """Copy a live version into a new head version.

        Existing versions never change; the new version records
        ``promoted_from_version_number``.
        """
        payload = self._generated(self._versions_api).create_promotion(
            _require_text(endpoint_id, "endpoint_id"),
            body={"version_id": _require_text(version_id, "version_id")},
        )
        return self._published(payload).head_version


__all__ = [
    "Endpoint",
    "EndpointPage",
    "EndpointVersion",
    "EndpointVersionPage",
    "EndpointsOperations",
]
