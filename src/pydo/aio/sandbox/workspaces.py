# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async persistent workspaces: ``/v2/sandboxes/workspaces``.

Hand-written; preserved across ``make generate``. The async twin of
:mod:`pydo.sandbox.workspaces`: same names, with ``await`` and ``async for``.

.. code-block:: python

    workspace = await Workspace.create(name="my-project", size_limit_gib=10)
    await workspace.wait_until_available()
    sandbox = await Sandbox.create(workspace_id=workspace.workspace_id)
"""

import asyncio
import time
from typing import Any, Optional

from pydo.sandbox import _workspaces as _w
from pydo.sandbox._connection import resolve
from pydo.sandbox._hybrid import by_id_or_self
from pydo.sandbox._workspaces import WorkspaceInfo, WorkspaceState
from pydo.sandbox.errors import NotFoundError, SandboxError, SandboxTimeoutError

from ._transport import call_raw as _call
from .templates import Pages


def _make_client(token: Optional[str], api_url: Optional[str]) -> Any:
    from pydo.aio import Client  # pylint: disable=import-outside-toplevel

    resolved, url = resolve(token, api_url)
    return Client(resolved, endpoint=url)


class Workspace:
    """A team persistent workspace (async)."""

    def __init__(self, client: Any, info: WorkspaceInfo) -> None:
        self._client = client
        #: The record as last returned by the API. Await :meth:`refresh` to update it.
        self.info = info

    def __repr__(self) -> str:
        return "Workspace(workspace_id=%r, name=%r, state=%r)" % (
            self.workspace_id,
            self.name,
            self.state,
        )

    @property
    def workspace_id(self) -> str:
        """The id ``Sandbox.create(workspace_id=...)`` takes."""
        return self.info.workspace_id

    @property
    def name(self) -> str:
        return self.info.name

    @property
    def state(self) -> WorkspaceState:
        return self.info.state

    @classmethod
    async def create(
        cls,
        *,
        size_limit_gib: int,
        name: Optional[str] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Workspace":
        """Creates a workspace. Returns as soon as the API accepts it."""
        body = _w.create_body(name, size_limit_gib)
        client = _make_client(token, api_url)
        try:
            res = await _call(client, "POST", _w.COLLECTION_PATH, body=body) or {}
            return cls(client, _w.to_workspace(res.get("workspace")))
        except BaseException:
            await client.close()
            raise

    @classmethod
    async def get(
        cls,
        workspace_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Workspace":
        """Fetches a workspace by id."""
        client = _make_client(token, api_url)
        try:
            return cls(client, await _fetch(client, workspace_id))
        except BaseException:
            await client.close()
            raise

    @classmethod
    def list(
        cls,
        *,
        state: Optional[WorkspaceState] = None,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> Pages:
        """Lists your team's workspaces. ``async for`` over it, or await ``next_items()``."""
        client = _make_client(token, api_url)

        async def fetch(page_token: Optional[str]):
            res = (
                await _call(
                    client,
                    "GET",
                    _w.COLLECTION_PATH,
                    params={
                        "state": state,
                        "page_size": limit,
                        "page_token": page_token,
                    },
                )
                or {}
            )
            items = [
                cls(client, _w.to_workspace(r)) for r in res.get("workspaces") or []
            ]
            return items, res.get("next_page_token")

        return Pages(fetch, next_token, close=client.close)

    async def refresh(self) -> WorkspaceInfo:
        """Reads the workspace again."""
        self.info = await _fetch(self._client, self.workspace_id)
        return self.info

    @by_id_or_self
    async def delete(self) -> bool:
        """Deletes the workspace. Also callable as ``await Workspace.delete(workspace_id)``."""
        return await _delete(self._client, self.workspace_id)

    @delete.by_id
    async def delete(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        workspace_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> bool:
        async with _make_client(token, api_url) as client:
            return await _delete(client, workspace_id)

    async def wait_until_available(
        self, *, timeout: float = 300.0, poll_interval: float = 2.0
    ) -> "Workspace":
        """Polls until the workspace can be attached. Raises if it failed or the wait runs out."""
        deadline = time.monotonic() + timeout
        while True:
            if self.state == _w.AVAILABLE:
                return self
            reason = _w.not_available_message(self.info)
            if reason:
                raise SandboxError(reason)
            if time.monotonic() >= deadline:
                raise SandboxTimeoutError(
                    "workspace %s was not available in time (last state %s)"
                    % (self.workspace_id, self.state)
                )
            await asyncio.sleep(poll_interval)
            await self.refresh()

    async def close(self) -> None:
        """Closes the HTTP connection. Does not delete the workspace."""
        await self._client.close()

    async def __aenter__(self) -> "Workspace":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()


async def _fetch(client: Any, workspace_id: str) -> WorkspaceInfo:
    res = await _call(client, "GET", _w.item_path(workspace_id)) or {}
    return _w.to_workspace(res.get("workspace"))


async def _delete(client: Any, workspace_id: str) -> bool:
    try:
        await _call(client, "DELETE", _w.item_path(workspace_id))
        return True
    except NotFoundError:
        return False


__all__ = ["Workspace", "WorkspaceInfo", "WorkspaceState"]
