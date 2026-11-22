# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async DigitalOcean Sandbox SDK over ``/v2/sandboxes``.

Hand-written; preserved across ``make generate``. The async twin of
:mod:`pydo.sandbox`: same names, with ``await`` and ``async for``.

.. code-block:: python

    from pydo.aio.sandbox import Sandbox

    async with await Sandbox.create(template="coding-base") as sandbox:
        await sandbox.pause()
        await sandbox.resume()
"""

import asyncio
import time
from typing import Any, AsyncIterator, List, Mapping, Optional

from pydo.sandbox import _snapshots as _snap
from pydo.sandbox import types as _t
from pydo.sandbox._connection import resolve
from pydo.sandbox._hybrid import by_id_or_self

from ._transport import call as _call
from .commands import Commands
from .snapshots import Snapshot, _create as _create_snapshot
from pydo.sandbox.errors import NotFoundError, SandboxError, SandboxTimeoutError
from pydo.sandbox.types import (
    SandboxInfo,
    SandboxState,
    create_body,
    require_id,
    to_info,
)


def _make_client(token: Optional[str], api_url: Optional[str]) -> Any:
    from pydo.aio import Client  # pylint: disable=import-outside-toplevel

    resolved, url = resolve(token, api_url)
    return Client(resolved, endpoint=url)


class Sandbox:
    """A DigitalOcean Sandbox (async).

    Create one with :meth:`create`, or find one with :meth:`get`,
    :meth:`connect` or :meth:`list`. Use ``async with`` to delete it at the end
    of the block, or call :meth:`close` when you are done with it.
    """

    def __init__(self, client: Any, info: SandboxInfo) -> None:
        self._client = client
        #: The record as last returned by the API. Await :meth:`get_info` to refresh it.
        self.info = info
        #: Start, list and stream the commands running in this sandbox.
        self.commands = Commands(client, info.sandbox_id)

    def __repr__(self) -> str:
        return "Sandbox(sandbox_id=%r, state=%r)" % (self.sandbox_id, self.state)

    @property
    def sandbox_id(self) -> str:
        return self.info.sandbox_id

    @property
    def state(self) -> SandboxState:
        return self.info.state

    @property
    def template(self) -> str:
        return self.info.template

    @classmethod
    async def create(
        cls,
        *,
        template: Optional[str] = None,
        size: Optional[str] = None,
        allow_internet_access: Optional[bool] = None,
        env_vars: Optional[Mapping[str, str]] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Sandbox":
        """Creates a sandbox. Returns once it is running. See :meth:`pydo.sandbox.Sandbox.create`."""
        body = create_body(template, size, allow_internet_access, env_vars)
        client = _make_client(token, api_url)
        try:
            return cls(client, to_info(await _call(client.sandboxes.create, body)))
        except BaseException:
            await client.close()
            raise

    @classmethod
    async def get(
        cls,
        sandbox_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Sandbox":
        """Fetches a sandbox by id."""
        client = _make_client(token, api_url)
        try:
            return cls(
                client,
                to_info(await _call(client.sandboxes.get, require_id(sandbox_id))),
            )
        except BaseException:
            await client.close()
            raise

    @classmethod
    async def connect(
        cls,
        sandbox_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Sandbox":
        """Fetches a sandbox by id and resumes it if it is paused."""
        sandbox = await cls.get(sandbox_id, token=token, api_url=api_url)
        if sandbox.state == _t.PAUSED:
            await sandbox.resume()
        return sandbox

    @classmethod
    def list(
        cls,
        *,
        state: Optional[SandboxState] = None,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "SandboxPaginator":
        """Lists the team's sandboxes. ``async for`` over it, or await :meth:`SandboxPaginator.next_items`."""
        return SandboxPaginator(
            _make_client(token, api_url),
            state=state,
            limit=limit,
            next_token=next_token,
        )

    async def get_info(self) -> SandboxInfo:
        """Reads the sandbox again."""
        self.info = to_info(await _call(self._client.sandboxes.get, self.sandbox_id))
        return self.info

    async def is_running(self) -> bool:
        """True when the sandbox is running right now. Reads the API."""
        return (await self.get_info()).state == _t.RUNNING

    async def resume(self) -> SandboxInfo:
        """Resumes a paused sandbox."""
        self.info = to_info(
            await _call(self._client.sandboxes.post_resume, self.sandbox_id)
        )
        return self.info

    @by_id_or_self
    async def pause(self) -> SandboxInfo:
        """Pauses the sandbox. Also callable as ``await Sandbox.pause(sandbox_id)``."""
        self.info = to_info(
            await _call(self._client.sandboxes.post_pause, self.sandbox_id)
        )
        return self.info

    @pause.by_id
    async def pause(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        sandbox_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> SandboxInfo:
        async with _make_client(token, api_url) as client:
            return to_info(
                await _call(client.sandboxes.post_pause, require_id(sandbox_id))
            )

    @by_id_or_self
    async def kill(self) -> bool:
        """Deletes the sandbox. Returns ``False`` when it is already gone.

        Also callable as ``await Sandbox.kill(sandbox_id)``.
        """
        return await _delete(self._client, self.sandbox_id)

    @kill.by_id
    async def kill(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        sandbox_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> bool:
        async with _make_client(token, api_url) as client:
            return await _delete(client, require_id(sandbox_id))

    async def create_snapshot(
        self, *, name: Optional[str] = None, ttl: Optional[str] = None
    ) -> Snapshot:
        """Starts a snapshot of this sandbox, which must be running or paused.

        Returns as soon as the snapshot is accepted, in the ``CREATING`` state.
        Await ``snapshot.wait_until_ready()`` before relying on it. The snapshot
        shares this sandbox's connection: closing the sandbox closes it too.
        """
        body = _snap.create_body(name, ttl)
        return await _create_snapshot(self._client, self.sandbox_id, body, False)

    async def wait_until_running(
        self, *, timeout: float = 120.0, poll_interval: float = 1.0
    ) -> "Sandbox":
        """Polls until the sandbox is running. Raises if it is paused or the wait runs out."""
        deadline = time.monotonic() + timeout
        while True:
            if self.state == _t.RUNNING:
                return self
            if self.state != _t.CREATING:
                raise SandboxError(
                    "sandbox %s will not become running: %s"
                    % (self.sandbox_id, self.state)
                )
            if time.monotonic() >= deadline:
                raise SandboxTimeoutError(
                    "sandbox %s was not running in time (last state %s)"
                    % (self.sandbox_id, self.state)
                )
            await asyncio.sleep(poll_interval)
            await self.get_info()

    async def close(self) -> None:
        """Closes the HTTP connection. Does not delete the sandbox."""
        await self._client.close()

    async def __aenter__(self) -> "Sandbox":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        """Deletes the sandbox and closes the connection."""
        try:
            await self.kill()
        finally:
            await self.close()


class SandboxPaginator:
    """One page at a time via :meth:`next_items`, or every sandbox with ``async for``.

    The connection closes when the last page has been read; call :meth:`close`
    if you stop early.
    """

    def __init__(
        self,
        client: Any,
        *,
        state: Optional[SandboxState],
        limit: Optional[int],
        next_token: Optional[str],
    ) -> None:
        self._client = client
        self._state = state
        self._limit = limit
        self._token = next_token or None
        self._started = False

    @property
    def has_next(self) -> bool:
        """True until a page came back without a next-page token."""
        return not self._started or self._token is not None

    @property
    def next_token(self) -> Optional[str]:
        """The token that resumes after the last page read, if there is one."""
        return self._token

    async def next_items(self) -> List[Sandbox]:
        """Reads the next page."""
        if not self.has_next:
            raise SandboxError("no more sandboxes to list")
        res = await _call(
            self._client.sandboxes.list,
            page_size=self._limit,
            page_token=self._token,
            state=self._state,
        )
        self._started = True
        self._token = (res or {}).get("next_page_token") or None
        return [
            Sandbox(self._client, to_info({"sandbox": item}))
            for item in (res or {}).get("sandboxes") or []
        ]

    async def close(self) -> None:
        """Closes the HTTP connection shared by the pages."""
        await self._client.close()

    async def __aiter__(self) -> AsyncIterator[Sandbox]:
        while self.has_next:
            for item in await self.next_items():
                yield item


async def _delete(client: Any, sandbox_id: str) -> bool:
    try:
        await _call(client.sandboxes.delete, sandbox_id)
        return True
    except NotFoundError:
        return False
