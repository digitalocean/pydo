# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async Hosted Agents API — hand-written; preserved across ``make generate``."""
from __future__ import annotations

from typing import Optional

from pydo.agents import resolve_agents_base_url
from pydo.custom_extensions import _BaseURLProxy

from .custom_sessions import AsyncHarnessEventStream, AsyncSessionsOperations


class AsyncAgentsResources:
    def __init__(self, parent_client, *, agents_endpoint: Optional[str] = None):
        self._proxy = _BaseURLProxy(
            parent_client._client,
            resolve_agents_base_url(agents_endpoint),
        )
        self.sessions = AsyncSessionsOperations(self._proxy)

    @property
    def base_url(self) -> str:
        return self._proxy._base_url


__all__ = ["AsyncAgentsResources", "AsyncSessionsOperations", "AsyncHarnessEventStream"]
