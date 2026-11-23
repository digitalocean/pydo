# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Migrating from Daytona (async): ``AsyncDaytona`` over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. Matches ``daytona`` 2.1.0. The
sync client is in :mod:`pydo.sandbox.compat.daytona`.

.. code-block:: python

    from pydo.aio.sandbox.compat.daytona import AsyncDaytona, DaytonaConfig

    async with AsyncDaytona(DaytonaConfig(api_key=token)) as daytona:
        sandbox = await daytona.create()
        print((await sandbox.process.exec("echo hello")).result)
"""

from typing import Any, Optional

from pydo.sandbox.compat.daytona import _mirror_v0 as _m0
from pydo.sandbox.compat.daytona._common import (
    SandboxState,
    SnapshotState,
    resolve_config,
)
from pydo.sandbox.compat.daytona.exceptions import *  # noqa: F401,F403  pylint: disable=wildcard-import,unused-wildcard-import
from . import v0 as _v0
from . import v2 as _v2
from .v0 import AsyncProcess, AsyncSandbox, AsyncSnapshotService

DaytonaConfig = _m0.DaytonaConfig

_HAND_WRITTEN = {
    "AsyncDaytona",
    "AsyncProcess",
    "AsyncSandbox",
    "AsyncSnapshotService",
    "SandboxState",
    "SnapshotState",
}

for _name, _value in vars(_m0).items():
    if _name[:1].isupper() and _name not in _HAND_WRITTEN and _name not in globals():
        globals()[_name] = _value
del _name, _value


class AsyncDaytonaClient:
    """Daytona's async root client, backed by DigitalOcean Sandboxes.

    The async twin of ``pydo.sandbox.compat.daytona.DaytonaClient``:
    ``client.v0`` and ``client.v2`` are the namespaces, and ``await
    client.create(...)`` and the other legacy calls are the ``v0`` ones.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        *,
        do_api_url: Optional[str] = None,
        size: Optional[str] = None,
    ) -> None:
        self._v0 = _v0.AsyncDaytona(config, do_api_url=do_api_url, size=size)
        resolved = resolve_config(
            "AsyncDaytona", config, {"do_api_url": do_api_url, "size": size}
        )
        self._v2 = _v2.AsyncDaytona(
            {"token": resolved["token"], "api_url": resolved["api_url"]},
            resolved["size"],
        )

    @property
    def v0(self) -> _v0.AsyncDaytona:
        return self._v0

    @property
    def v2(self) -> _v2.AsyncDaytona:
        return self._v2

    @property
    def snapshot(self) -> AsyncSnapshotService:
        return self._v0.snapshot

    @property
    def volume(self) -> Any:
        return self._v0.volume

    async def create(self, *args: Any, **kwargs: Any) -> AsyncSandbox:
        return await self._v0.create(*args, **kwargs)

    async def get(self, *args: Any, **kwargs: Any) -> AsyncSandbox:
        return await self._v0.get(*args, **kwargs)

    async def list(self, *args: Any, **kwargs: Any) -> Any:
        return await self._v0.list(*args, **kwargs)

    async def start(self, *args: Any, **kwargs: Any) -> None:
        await self._v0.start(*args, **kwargs)

    async def stop(self, *args: Any, **kwargs: Any) -> None:
        await self._v0.stop(*args, **kwargs)

    async def delete(self, *args: Any, **kwargs: Any) -> None:
        await self._v0.delete(*args, **kwargs)

    async def close(self) -> None:
        """Nothing to close: each call manages its own connection."""

    async def __aenter__(self) -> "AsyncDaytonaClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()


#: Daytona's own name for the async client, so ``from daytona import AsyncDaytona`` becomes an import swap.
AsyncDaytona = AsyncDaytonaClient
