# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Migrating from E2B: the E2B Python SDK's names over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. Matches ``e2b`` 2.64.0.

Change the import, nothing else:

.. code-block:: python

    from pydo.sandbox.compat.e2b import Sandbox   # was: from e2b import Sandbox

    sandbox = Sandbox.create(api_key=os.environ["DIGITALOCEAN_ACCESS_TOKEN"])
    result = sandbox.commands.run("echo hello")
    sandbox.kill()

or bind a token once with :class:`E2bClient`. Whatever DigitalOcean Sandboxes
cannot do yet (files, PTY, git, ports, volumes, lifetime timeouts, metadata) keeps
E2B's signature and raises
:class:`~pydo.sandbox.errors.SandboxNotImplementedError`. The async classes
(``AsyncSandbox``) are in :mod:`pydo.aio.sandbox.compat.e2b`.
"""

from typing import Any, Dict, Optional

from . import _mirror as _m
from ._common import CommandExitException, CommandResult, SandboxState
from .exceptions import *  # noqa: F401,F403  pylint: disable=wildcard-import,unused-wildcard-import
from .sandbox import (
    CommandHandle,
    Commands,
    Sandbox,
    SandboxPaginator,
    SnapshotPaginator,
)

_HAND_WRITTEN = {
    "CommandExitException",
    "CommandHandle",
    "CommandResult",
    "Commands",
    "Sandbox",
    "SandboxPaginator",
    "SandboxState",
    "SnapshotPaginator",
}

# Everything else E2B exports is the generated signature mirror: every public
# class and function raises SandboxNotImplementedError until it is wired up.
for _name, _value in vars(_m).items():
    if _name[:1].isupper() and _name not in _HAND_WRITTEN and _name not in globals():
        globals()[_name] = _value
del _name, _value

_CLIENT_SIDE = (
    "request_timeout",
    "retries",
    "headers",
    "api_headers",
    "validate_api_key",
    "debug",
    "proxy",
    "http_version",
)


class E2bClient:
    """Binds a DigitalOcean token once, like ``SandboxClient``, with E2B's names.

    ``api_key`` is the DigitalOcean API token (default: ``DIGITALOCEAN_ACCESS_TOKEN``).
    E2B's HTTP options (``request_timeout``, ``retries``, ``headers``, ``debug``,
    ``proxy``, ``http_version``) are accepted and ignored. ``domain``, ``api_url``
    and ``sandbox_url`` name E2B's servers and raise. ``do_api_url`` and ``size``
    are DigitalOcean extras: another API origin, and the size slug E2B's
    ``cpu_count`` stands for.

    .. code-block:: python

        client = E2bClient(api_key=token)
        sandbox = client.Sandbox.create(template="coding-base")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        do_api_url: Optional[str] = None,
        size: Optional[str] = None,
        **opts: Any,
    ) -> None:
        from ._common import connection  # pylint: disable=import-outside-toplevel

        connection("E2bClient", opts, {})
        unknown = set(opts) - set(_CLIENT_SIDE) - {"domain", "api_url", "sandbox_url"}
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
        #: ``Sandbox`` with this client's token filled in.
        self.Sandbox = type(
            "Sandbox", (Sandbox,), {"_defaults": defaults}
        )  # pylint: disable=invalid-name
        #: E2B's ``Template`` (every method raises ``SandboxNotImplementedError``).
        self.Template = _m.Template  # pylint: disable=invalid-name
        #: E2B's ``Volume`` (every method raises ``SandboxNotImplementedError``).
        self.Volume = _m.Volume  # pylint: disable=invalid-name
        #: E2B's ``Secret`` (every method raises ``SandboxNotImplementedError``).
        self.Secret = _m.Secret  # pylint: disable=invalid-name
