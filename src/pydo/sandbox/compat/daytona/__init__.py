# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Migrating from Daytona: the Daytona Python SDK's names over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. Matches ``daytona`` 2.1.0 (and
the shapes of the legacy ``daytona-sdk`` 0.233.0).

Change the import, nothing else:

.. code-block:: python

    from pydo.sandbox.compat.daytona import Daytona, DaytonaConfig   # was: from daytona import ...

    daytona = Daytona(DaytonaConfig(api_key=os.environ["DIGITALOCEAN_ACCESS_TOKEN"]))
    sandbox = daytona.create()
    print(sandbox.process.exec("echo hello").result)
    daytona.delete(sandbox)

``Daytona().v0`` and ``Daytona().v2`` are the two namespaces of daytona 2.1.0; the
legacy top-level calls (``daytona.create(...)``) are the ``v0`` ones. Whatever
DigitalOcean Sandboxes cannot do yet keeps Daytona's signature and raises
:class:`~pydo.sandbox.errors.SandboxNotImplementedError`. The async client
(``AsyncDaytona``) is in :mod:`pydo.aio.sandbox.compat.daytona`.
"""

from typing import Any, Optional

from . import _mirror_v0 as _m0
from . import v0 as _v0
from . import v2 as _v2
from ._common import SandboxState, SnapshotState, resolve_config
from .exceptions import *  # noqa: F401,F403  pylint: disable=wildcard-import,unused-wildcard-import
from .v0 import Process, Sandbox, Snapshot, SnapshotService

DaytonaConfig = _m0.DaytonaConfig

_HAND_WRITTEN = {
    "Daytona",
    "Process",
    "Sandbox",
    "SandboxState",
    "Snapshot",
    "SnapshotService",
    "SnapshotState",
}

# Everything else the v0 namespace exports is the generated signature mirror.
for _name, _value in vars(_m0).items():
    if _name[:1].isupper() and _name not in _HAND_WRITTEN and _name not in globals():
        globals()[_name] = _value
del _name, _value


class DaytonaClient:
    """Daytona's root client, backed by DigitalOcean Sandboxes.

    ``config.api_key`` is the DigitalOcean API token (default
    ``DIGITALOCEAN_ACCESS_TOKEN``; ``DAYTONA_API_KEY`` is not read). Fields that
    point at Daytona (``api_url``, ``server_url``, ``jwt_token``,
    ``organization_id``, ``project_id``, ``target``, ``events``) raise; HTTP tuning
    fields are accepted and ignored. ``do_api_url`` and ``size`` are DigitalOcean
    extras: another API origin, and the size slug Daytona's ``resources`` stand for.

    ``client.v0`` and ``client.v2`` are the two namespaces; ``client.create(...)``,
    ``get``, ``list``, ``start``, ``stop`` and ``delete`` are the ``v0`` ones.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        *,
        do_api_url: Optional[str] = None,
        size: Optional[str] = None,
    ) -> None:
        self._v0 = _v0.Daytona(config, do_api_url=do_api_url, size=size)
        resolved = resolve_config(
            "Daytona", config, {"do_api_url": do_api_url, "size": size}
        )
        self._v2 = _v2.Daytona(
            {"token": resolved["token"], "api_url": resolved["api_url"]},
            resolved["size"],
        )

    @property
    def v0(self) -> _v0.Daytona:
        return self._v0

    @property
    def v2(self) -> _v2.Daytona:
        return self._v2

    @property
    def snapshot(self) -> SnapshotService:
        return self._v0.snapshot

    @property
    def volume(self) -> Any:
        return self._v0.volume

    def create(self, *args: Any, **kwargs: Any) -> Sandbox:
        """``v0`` create: see :meth:`pydo.sandbox.compat.daytona.v0.Daytona.create`."""
        return self._v0.create(*args, **kwargs)

    def get(self, *args: Any, **kwargs: Any) -> Sandbox:
        return self._v0.get(*args, **kwargs)

    def list(self, *args: Any, **kwargs: Any) -> Any:
        return self._v0.list(*args, **kwargs)

    def start(self, *args: Any, **kwargs: Any) -> None:
        self._v0.start(*args, **kwargs)

    def stop(self, *args: Any, **kwargs: Any) -> None:
        self._v0.stop(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> None:
        self._v0.delete(*args, **kwargs)

    def close(self) -> None:
        """Nothing to close: each call manages its own connection."""

    def __enter__(self) -> "DaytonaClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


#: Daytona's own name for the sync client, so ``from daytona import Daytona`` becomes an import swap.
Daytona = DaytonaClient
