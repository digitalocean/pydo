# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Persistent workspaces: ``/v2/sandboxes/workspaces``.

Hand-written; preserved across ``make generate``. A workspace is a durable disk
that outlives any one sandbox. Create one, wait until it is available, then pass
its id to ``Sandbox.create``.

The generated client has no workspace operations yet, so the requests are sent
through ``client.send_request`` (see :func:`pydo.sandbox._transport.call_raw`).

.. code-block:: python

    workspace = Workspace.create(name="my-project", size_limit_gib=10)
    workspace.wait_until_available()
    sandbox = Sandbox.create(workspace_id=workspace.workspace_id)
"""

import time
from typing import Any, Optional

from . import _workspaces as _w
from ._connection import resolve
from ._hybrid import by_id_or_self
from ._transport import call_raw as _call
from ._workspaces import WorkspaceInfo, WorkspaceState
from .errors import NotFoundError, SandboxTimeoutError, SandboxError
from .templates import Pages


def _make_client(token: Optional[str], api_url: Optional[str]) -> Any:
    from pydo import Client  # pylint: disable=import-outside-toplevel

    resolved, url = resolve(token, api_url)
    return Client(resolved, endpoint=url)


class Workspace:
    """A team persistent workspace."""

    def __init__(self, client: Any, info: WorkspaceInfo) -> None:
        self._client = client
        #: The record as last returned by the API. Call :meth:`refresh` to update it.
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
    def create(
        cls,
        *,
        size_limit_gib: int,
        name: Optional[str] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Workspace":
        """Creates a workspace. Returns as soon as the API accepts it.

        Call :meth:`wait_until_available` before attaching it to a sandbox.

        :keyword size_limit_gib: The size limit in GiB. The API allows at most 100.
        :keyword name: An optional label.
        """
        body = _w.create_body(name, size_limit_gib)
        client = _make_client(token, api_url)
        try:
            res = _call(client, "POST", _w.COLLECTION_PATH, body=body) or {}
            return cls(client, _w.to_workspace(res.get("workspace")))
        except BaseException:
            client.close()
            raise

    @classmethod
    def get(
        cls,
        workspace_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Workspace":
        """Fetches a workspace by id."""
        client = _make_client(token, api_url)
        try:
            return cls(client, _fetch(client, workspace_id))
        except BaseException:
            client.close()
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
        """Lists your team's workspaces, optionally only those in ``state``."""
        client = _make_client(token, api_url)

        def fetch(page_token: Optional[str]):
            res = (
                _call(
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

        return Pages(fetch, next_token)

    def refresh(self) -> WorkspaceInfo:
        """Reads the workspace again."""
        self.info = _fetch(self._client, self.workspace_id)
        return self.info

    @by_id_or_self
    def delete(self) -> bool:
        """Deletes the workspace and its data. Returns ``False`` when it is already gone.

        The API refuses (409) while a sandbox has it attached. Also callable as
        ``Workspace.delete(workspace_id)``.
        """
        return _delete(self._client, self.workspace_id)

    @delete.by_id
    def delete(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        workspace_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> bool:
        with _make_client(token, api_url) as client:
            return _delete(client, workspace_id)

    def wait_until_available(
        self, *, timeout: float = 300.0, poll_interval: float = 2.0
    ) -> "Workspace":
        """Polls until the workspace can be attached to a sandbox.

        Raises if the workspace failed or is being deleted, or the wait runs out.
        """
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
            time.sleep(poll_interval)
            self.refresh()

    def close(self) -> None:
        """Closes the HTTP connection. Does not delete the workspace."""
        self._client.close()

    def __enter__(self) -> "Workspace":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


def _fetch(client: Any, workspace_id: str) -> WorkspaceInfo:
    res = _call(client, "GET", _w.item_path(workspace_id)) or {}
    return _w.to_workspace(res.get("workspace"))


def _delete(client: Any, workspace_id: str) -> bool:
    try:
        _call(client, "DELETE", _w.item_path(workspace_id))
        return True
    except NotFoundError:
        return False


__all__ = ["Workspace", "WorkspaceInfo", "WorkspaceState"]
