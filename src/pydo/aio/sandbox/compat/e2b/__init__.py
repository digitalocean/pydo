# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Migrating from E2B (async): ``AsyncSandbox`` over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. Matches ``e2b`` 2.64.0. The sync
classes are in :mod:`pydo.sandbox.compat.e2b`.

.. code-block:: python

    from pydo.aio.sandbox.compat.e2b import AsyncSandbox   # was: from e2b import AsyncSandbox

    sandbox = await AsyncSandbox.create(api_key=token)
    result = await sandbox.commands.run("echo hello")
    await sandbox.kill()
"""

from typing import Any, Dict, Optional

from pydo.sandbox.compat.e2b import _mirror as _m
from pydo.sandbox.compat.e2b._common import (
    CLIENT_SIDE_OPTIONS,
    CommandExitException,
    CommandResult,
    SandboxState,
    connection,
)
from pydo.sandbox.compat.e2b.exceptions import *  # noqa: F401,F403  pylint: disable=wildcard-import,unused-wildcard-import
from .sandbox import (
    AsyncCommandHandle,
    AsyncCommands,
    AsyncSandbox,
    AsyncSandboxPaginator,
    AsyncSnapshotPaginator,
)

_HAND_WRITTEN = {
    "AsyncCommandHandle",
    "AsyncCommands",
    "AsyncSandbox",
    "AsyncSandboxPaginator",
    "AsyncSnapshotPaginator",
    "CommandExitException",
    "CommandResult",
    "SandboxState",
}

for _name, _value in vars(_m).items():
    if _name[:1].isupper() and _name not in _HAND_WRITTEN and _name not in globals():
        globals()[_name] = _value
del _name, _value


class E2bClient:
    """Async twin of ``pydo.sandbox.compat.e2b.E2bClient``: binds a token once.

    ``client.AsyncSandbox`` is ``AsyncSandbox`` with the token filled in.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        do_api_url: Optional[str] = None,
        size: Optional[str] = None,
        **opts: Any,
    ) -> None:
        connection("E2bClient", opts, {})
        unknown = (
            set(opts) - set(CLIENT_SIDE_OPTIONS) - {"domain", "api_url", "sandbox_url"}
        )
        if unknown:
            raise TypeError(
                "E2bClient() got unexpected keyword arguments: %s"
                % ", ".join(sorted(unknown))
            )
        defaults: Dict[str, Any] = {
            "token": api_key,
            "api_url": do_api_url,
            "size": size,
        }
        self.AsyncSandbox = type(
            "AsyncSandbox", (AsyncSandbox,), {"_defaults": defaults}
        )  # pylint: disable=invalid-name
        self.AsyncTemplate = _m.AsyncTemplate  # pylint: disable=invalid-name
        self.AsyncVolume = _m.AsyncVolume  # pylint: disable=invalid-name
        self.AsyncSecret = _m.AsyncSecret  # pylint: disable=invalid-name
