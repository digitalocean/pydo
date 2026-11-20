# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Binds a token and API origin once (async)."""

from typing import Mapping, Optional

from pydo.sandbox.types import SandboxInfo, SandboxState

from .sandbox import Sandbox, SandboxPaginator


class _BoundSandbox:
    """``Sandbox`` with the client's token and API origin filled in."""

    def __init__(self, token: Optional[str], api_url: Optional[str]) -> None:
        self._conn = {"token": token, "api_url": api_url}

    async def create(
        self,
        *,
        template: Optional[str] = None,
        size: Optional[str] = None,
        allow_internet_access: Optional[bool] = None,
        env_vars: Optional[Mapping[str, str]] = None,
    ) -> Sandbox:
        return await Sandbox.create(
            template=template,
            size=size,
            allow_internet_access=allow_internet_access,
            env_vars=env_vars,
            **self._conn,
        )

    async def get(self, sandbox_id: str) -> Sandbox:
        return await Sandbox.get(sandbox_id, **self._conn)

    async def connect(self, sandbox_id: str) -> Sandbox:
        return await Sandbox.connect(sandbox_id, **self._conn)

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

    async def kill(self, sandbox_id: str) -> bool:
        return await Sandbox.kill(sandbox_id, **self._conn)

    async def pause(self, sandbox_id: str) -> SandboxInfo:
        return await Sandbox.pause(sandbox_id, **self._conn)


class SandboxClient:
    """Binds connection options once.

    .. code-block:: python

        client = SandboxClient(token=os.environ["DIGITALOCEAN_ACCESS_TOKEN"])
        sandbox = await client.Sandbox.create(template="coding-base")
    """

    def __init__(
        self, *, token: Optional[str] = None, api_url: Optional[str] = None
    ) -> None:
        self.Sandbox = _BoundSandbox(token, api_url)  # pylint: disable=invalid-name


__all__ = ["SandboxClient"]
