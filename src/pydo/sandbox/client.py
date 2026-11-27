# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Binds a token and API origin once."""

from typing import Mapping, Optional

from .sandbox import Sandbox, SandboxPaginator
from .snapshots import Snapshot
from .templates import Pages, Template
from ._workspaces import WorkspaceState
from .types import SandboxInfo, SandboxState
from .workspaces import Workspace


class _BoundSandbox:
    """``Sandbox`` with the client's token and API origin filled in."""

    def __init__(self, token: Optional[str], api_url: Optional[str]) -> None:
        self._conn = {"token": token, "api_url": api_url}

    def create(
        self,
        *,
        template: Optional[str] = None,
        size: Optional[str] = None,
        allow_internet_access: Optional[bool] = None,
        env_vars: Optional[Mapping[str, str]] = None,
        workspace_id: Optional[str] = None,
    ) -> Sandbox:
        return Sandbox.create(
            template=template,
            size=size,
            allow_internet_access=allow_internet_access,
            env_vars=env_vars,
            workspace_id=workspace_id,
            **self._conn,
        )

    def get(self, sandbox_id: str) -> Sandbox:
        return Sandbox.get(sandbox_id, **self._conn)

    def connect(self, sandbox_id: str) -> Sandbox:
        return Sandbox.connect(sandbox_id, **self._conn)

    def list(
        self,
        *,
        state: Optional[SandboxState] = None,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> SandboxPaginator:
        return Sandbox.list(
            state=state, limit=limit, next_token=next_token, **self._conn
        )

    def kill(self, sandbox_id: str) -> bool:
        return Sandbox.kill(sandbox_id, **self._conn)

    def pause(self, sandbox_id: str) -> SandboxInfo:
        return Sandbox.pause(sandbox_id, **self._conn)


class _BoundTemplate:
    """``Template`` with the client's token and API origin filled in."""

    def __init__(self, token: Optional[str], api_url: Optional[str]) -> None:
        self._conn = {"token": token, "api_url": api_url}

    def create(
        self, *, name: str, source_oci_ref: str, base_template: Optional[str] = None
    ) -> Template:
        return Template.create(
            name=name,
            source_oci_ref=source_oci_ref,
            base_template=base_template,
            **self._conn,
        )

    def get(self, template_id: str) -> Template:
        return Template.get(template_id, **self._conn)

    def list(
        self, *, limit: Optional[int] = None, next_token: Optional[str] = None
    ) -> Pages:
        return Template.list(limit=limit, next_token=next_token, **self._conn)

    def delete(self, template_id: str) -> bool:
        return Template.delete(template_id, **self._conn)


class _BoundSnapshot:
    """``Snapshot`` with the client's token and API origin filled in."""

    def __init__(self, token: Optional[str], api_url: Optional[str]) -> None:
        self._conn = {"token": token, "api_url": api_url}

    def create(
        self,
        sandbox_id: str,
        *,
        name: Optional[str] = None,
        ttl: Optional[str] = None,
    ) -> Snapshot:
        return Snapshot.create(sandbox_id, name=name, ttl=ttl, **self._conn)

    def get(self, snapshot_id: str) -> Snapshot:
        return Snapshot.get(snapshot_id, **self._conn)

    def list(
        self,
        *,
        sandbox_id: Optional[str] = None,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> Pages:
        return Snapshot.list(
            sandbox_id=sandbox_id, limit=limit, next_token=next_token, **self._conn
        )

    def delete(self, snapshot_id: str) -> bool:
        return Snapshot.delete(snapshot_id, **self._conn)


class _BoundWorkspace:
    """``Workspace`` with the client's token and API origin filled in."""

    def __init__(self, token: Optional[str], api_url: Optional[str]) -> None:
        self._conn = {"token": token, "api_url": api_url}

    def create(self, *, size_limit_gib: int, name: Optional[str] = None) -> Workspace:
        return Workspace.create(size_limit_gib=size_limit_gib, name=name, **self._conn)

    def get(self, workspace_id: str) -> Workspace:
        return Workspace.get(workspace_id, **self._conn)

    def list(
        self,
        *,
        state: Optional[WorkspaceState] = None,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> Pages:
        return Workspace.list(
            state=state, limit=limit, next_token=next_token, **self._conn
        )

    def delete(self, workspace_id: str) -> bool:
        return Workspace.delete(workspace_id, **self._conn)


class SandboxClient:
    """Binds connection options once.

    .. code-block:: python

        client = SandboxClient(token=os.environ["DIGITALOCEAN_ACCESS_TOKEN"])
        sandbox = client.Sandbox.create(template="coding-base")
    """

    def __init__(
        self, *, token: Optional[str] = None, api_url: Optional[str] = None
    ) -> None:
        self.Sandbox = _BoundSandbox(token, api_url)  # pylint: disable=invalid-name
        self.Template = _BoundTemplate(token, api_url)  # pylint: disable=invalid-name
        self.Snapshot = _BoundSnapshot(token, api_url)  # pylint: disable=invalid-name
        self.Workspace = _BoundWorkspace(token, api_url)  # pylint: disable=invalid-name


__all__ = ["SandboxClient"]
