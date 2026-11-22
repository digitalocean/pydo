# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async sandbox snapshots: ``/v2/sandboxes/snapshots``.

Hand-written; preserved across ``make generate``. The async twin of
:mod:`pydo.sandbox.snapshots`: same names, with ``await`` and ``async for``.

.. code-block:: python

    snapshot = await sandbox.create_snapshot(name="before-upgrade")
    await snapshot.wait_until_ready()
"""

import asyncio
import time
from typing import Any, Optional

from pydo.sandbox import _snapshots as _s
from pydo.sandbox._connection import resolve
from pydo.sandbox._hybrid import by_id_or_self
from pydo.sandbox._snapshots import SnapshotInfo, SnapshotState
from pydo.sandbox.errors import NotFoundError, SandboxError, SandboxTimeoutError

from ._transport import call as _call
from .templates import Pages


def _make_client(token: Optional[str], api_url: Optional[str]) -> Any:
    from pydo.aio import Client  # pylint: disable=import-outside-toplevel

    resolved, url = resolve(token, api_url)
    return Client(resolved, endpoint=url)


class Snapshot:
    """A sandbox snapshot (async)."""

    def __init__(
        self, client: Any, info: SnapshotInfo, owns_client: bool = True
    ) -> None:
        self._client = client
        self._owns_client = owns_client
        #: The record as last returned by the API. Await :meth:`refresh` to update it.
        self.info = info

    def __repr__(self) -> str:
        return "Snapshot(snapshot_id=%r, sandbox_id=%r, state=%r)" % (
            self.snapshot_id,
            self.sandbox_id,
            self.state,
        )

    @property
    def snapshot_id(self) -> str:
        return self.info.snapshot_id

    @property
    def sandbox_id(self) -> str:
        """The sandbox the snapshot was taken from."""
        return self.info.sandbox_id

    @property
    def name(self) -> Optional[str]:
        return self.info.name

    @property
    def state(self) -> SnapshotState:
        return self.info.state

    @classmethod
    async def create(
        cls,
        sandbox_id: str,
        *,
        name: Optional[str] = None,
        ttl: Optional[str] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Snapshot":
        """Starts a snapshot of a running or paused sandbox. Returns once it is accepted."""
        body = _s.create_body(name, ttl)
        client = _make_client(token, api_url)
        try:
            return await _create(client, sandbox_id, body, True)
        except BaseException:
            await client.close()
            raise

    @classmethod
    async def get(
        cls,
        snapshot_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Snapshot":
        """Fetches a snapshot by id."""
        client = _make_client(token, api_url)
        try:
            return cls(client, await _fetch(client, snapshot_id))
        except BaseException:
            await client.close()
            raise

    @classmethod
    def list(
        cls,
        *,
        sandbox_id: Optional[str] = None,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> Pages:
        """Lists your team's snapshots, newest first. ``async for`` over it, or await ``next_items()``."""
        client = _make_client(token, api_url)

        async def fetch(page_token: Optional[str]):
            res = (
                await _call(
                    client.sandboxes.list_snapshots,
                    sandbox_id=sandbox_id,
                    page_size=limit,
                    page_token=page_token,
                )
                or {}
            )
            items = [
                cls(client, _s.to_snapshot(r), False)
                for r in res.get("snapshots") or []
            ]
            return items, res.get("next_page_token")

        return Pages(fetch, next_token, close=client.close)

    async def refresh(self) -> SnapshotInfo:
        """Reads the snapshot again."""
        self.info = await _fetch(self._client, self.snapshot_id)
        return self.info

    @by_id_or_self
    async def delete(self) -> bool:
        """Deletes the snapshot. Also callable as ``await Snapshot.delete(snapshot_id)``."""
        return await _delete(self._client, self.snapshot_id)

    @delete.by_id
    async def delete(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        snapshot_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> bool:
        async with _make_client(token, api_url) as client:
            return await _delete(client, _s.require_snapshot_id(snapshot_id))

    async def wait_until_ready(
        self, *, timeout: float = 300.0, poll_interval: float = 2.0
    ) -> "Snapshot":
        """Polls until the snapshot is complete. Raises if it failed or the wait runs out."""
        deadline = time.monotonic() + timeout
        while True:
            if self.state == _s.COMPLETE:
                return self
            if self.state == _s.FAILED:
                raise SandboxError(_s.failure_message(self.info))
            if time.monotonic() >= deadline:
                raise SandboxTimeoutError(
                    "snapshot %s was not complete in time (last state %s)"
                    % (self.snapshot_id, self.state)
                )
            await asyncio.sleep(poll_interval)
            await self.refresh()

    async def close(self) -> None:
        """Closes the HTTP connection, unless it is shared with a sandbox. Does not delete the snapshot."""
        if self._owns_client:
            await self._client.close()

    async def __aenter__(self) -> "Snapshot":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()


async def _create(
    client: Any, sandbox_id: str, body: Any, owns_client: bool
) -> Snapshot:
    if not sandbox_id or not str(sandbox_id).strip():
        raise SandboxError("`sandbox_id` is required")
    res = await _call(client.sandboxes.create_snapshot, sandbox_id, body) or {}
    return Snapshot(client, _s.to_snapshot(res.get("snapshot")), owns_client)


async def _fetch(client: Any, snapshot_id: str) -> SnapshotInfo:
    res = (
        await _call(client.sandboxes.get_snapshot, _s.require_snapshot_id(snapshot_id))
        or {}
    )
    return _s.to_snapshot(res.get("snapshot"))


async def _delete(client: Any, snapshot_id: str) -> bool:
    try:
        await _call(client.sandboxes.delete_snapshot, snapshot_id)
        return True
    except NotFoundError:
        return False


__all__ = ["Snapshot", "SnapshotInfo", "SnapshotState"]
