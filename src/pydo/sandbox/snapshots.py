# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Sandbox snapshots: ``/v2/sandboxes/snapshots``.

Hand-written; preserved across ``make generate``. A snapshot captures the boot
disk and memory of a running or paused sandbox, not its workspace data disk.
Creation is asynchronous: create returns in the ``CREATING`` state, and
:meth:`Snapshot.wait_until_ready` polls until it is complete.

.. code-block:: python

    snapshot = sandbox.create_snapshot(name="before-upgrade")
    snapshot.wait_until_ready()
    print(snapshot.info.size_bytes)
"""

import time
from typing import Any, Optional

from . import _snapshots as _s
from ._connection import resolve
from ._hybrid import by_id_or_self
from ._snapshots import SnapshotInfo, SnapshotState
from ._transport import call as _call
from .errors import NotFoundError, SandboxError, SandboxTimeoutError
from .templates import Pages


def _make_client(token: Optional[str], api_url: Optional[str]) -> Any:
    from pydo import Client  # pylint: disable=import-outside-toplevel

    resolved, url = resolve(token, api_url)
    return Client(resolved, endpoint=url)


class Snapshot:
    """A sandbox snapshot."""

    def __init__(
        self, client: Any, info: SnapshotInfo, owns_client: bool = True
    ) -> None:
        self._client = client
        self._owns_client = owns_client
        #: The record as last returned by the API. Call :meth:`refresh` to update it.
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
    def create(
        cls,
        sandbox_id: str,
        *,
        name: Optional[str] = None,
        ttl: Optional[str] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Snapshot":
        """Starts a snapshot of a running or paused sandbox.

        Returns as soon as the snapshot is accepted. Call :meth:`wait_until_ready`
        before relying on it.

        :param sandbox_id: The sandbox to snapshot.
        :keyword name: Optional name: 1 to 63 lowercase letters, digits and hyphens.
        :keyword ttl: How long to keep the snapshot, such as ``168h``. Defaults to the platform's.
        """
        body = _s.create_body(name, ttl)
        client = _make_client(token, api_url)
        try:
            return _create(client, sandbox_id, body, True)
        except BaseException:
            client.close()
            raise

    @classmethod
    def get(
        cls,
        snapshot_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Snapshot":
        """Fetches a snapshot by id."""
        client = _make_client(token, api_url)
        try:
            return cls(client, _fetch(client, snapshot_id))
        except BaseException:
            client.close()
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
        """Lists your team's snapshots, newest first.

        :keyword sandbox_id: Only the snapshots of this sandbox.
        """
        client = _make_client(token, api_url)

        def fetch(page_token: Optional[str]):
            res = (
                _call(
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

        return Pages(fetch, next_token)

    def refresh(self) -> SnapshotInfo:
        """Reads the snapshot again."""
        self.info = _fetch(self._client, self.snapshot_id)
        return self.info

    @by_id_or_self
    def delete(self) -> bool:
        """Deletes the snapshot. Returns ``False`` when it is already gone.

        Sandboxes already started from it are not affected. Also callable as
        ``Snapshot.delete(snapshot_id)``.
        """
        return _delete(self._client, self.snapshot_id)

    @delete.by_id
    def delete(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        snapshot_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> bool:
        with _make_client(token, api_url) as client:
            return _delete(client, _s.require_snapshot_id(snapshot_id))

    def wait_until_ready(
        self, *, timeout: float = 300.0, poll_interval: float = 2.0
    ) -> "Snapshot":
        """Polls until the snapshot is complete.

        Raises if the snapshot failed (with the API's error message, when there
        is one) or the wait runs out.
        """
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
            time.sleep(poll_interval)
            self.refresh()

    def close(self) -> None:
        """Closes the HTTP connection, unless it is shared with a sandbox. Does not delete the snapshot."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "Snapshot":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


def _create(client: Any, sandbox_id: str, body: Any, owns_client: bool) -> Snapshot:
    if not sandbox_id or not str(sandbox_id).strip():
        raise SandboxError("`sandbox_id` is required")
    res = _call(client.sandboxes.create_snapshot, sandbox_id, body) or {}
    return Snapshot(client, _s.to_snapshot(res.get("snapshot")), owns_client)


def _fetch(client: Any, snapshot_id: str) -> SnapshotInfo:
    res = (
        _call(client.sandboxes.get_snapshot, _s.require_snapshot_id(snapshot_id)) or {}
    )
    return _s.to_snapshot(res.get("snapshot"))


def _delete(client: Any, snapshot_id: str) -> bool:
    try:
        _call(client.sandboxes.delete_snapshot, snapshot_id)
        return True
    except NotFoundError:
        return False


__all__ = ["Snapshot", "SnapshotInfo", "SnapshotState"]
