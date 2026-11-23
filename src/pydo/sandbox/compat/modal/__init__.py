# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Migrating from Modal: the Modal Python SDK's Sandbox names over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. Matches ``modal`` 1.6.4. Scope is
what Modal's Sandbox API covers: ``Sandbox``, ``App`` (as a grouping label),
``Image``, ``Secret``, ``Volume`` and ``Client``. Functions, classes, web endpoints,
Dicts and Queues are Modal products with no counterpart here.

Change the import, nothing else:

.. code-block:: python

    import pydo.sandbox.compat.modal as modal   # was: import modal

    app = modal.App.lookup("my-app", create_if_missing=True)
    sb = modal.Sandbox.create(app=app, image=modal.Image.debian_slim(), cpu=1, memory=1024)
    p = sb.exec("python3", "-c", "print('hello')")
    print(p.stdout.read())
    sb.terminate()

``await modal.Sandbox.create.aio(...)`` runs on the asynchronous Sandboxes SDK
(``pydo.aio``). Whatever DigitalOcean Sandboxes cannot do yet keeps Modal's
signature and raises :class:`~pydo.sandbox.errors.SandboxNotImplementedError`.
"""

from typing import Any, Dict, Optional

from . import _mirror as _m
from .._base import ModalMethod
from . import exceptions as exception
from ._common import Image, Secret, StreamType
from .sandbox import ContainerProcess, Sandbox, StreamReader, StreamWriter


class App(_m.App):
    """A Modal ``App``, here only a label that groups sandboxes (nothing is created)."""

    def __init__(
        self, name: Optional[str] = None, **kwargs: Any
    ) -> None:  # pylint: disable=super-init-not-called
        self._name = name
        self._kwargs = kwargs

    @property
    def name(self) -> Optional[str]:
        return self._name

    @property
    def app_id(self) -> Optional[str]:
        return "ap-" + self._name if self._name else None

    @property
    def description(self) -> Optional[str]:
        return self._name

    def _lookup_sync(cls, name: str, *, client: Optional[Any] = None, environment_name: Optional[str] = None, create_if_missing: bool = False) -> "App":  # type: ignore[misc]  # pylint: disable=no-self-argument
        return App(name)

    async def _lookup_aio(cls, name: str, *, client: Optional[Any] = None, environment_name: Optional[str] = None, create_if_missing: bool = False) -> "App":  # type: ignore[misc]  # pylint: disable=no-self-argument
        return App(name)

    lookup = ModalMethod(_lookup_sync, _lookup_aio, "classmethod")


class Client(_m.Client):
    """A Modal ``Client``: carries the DigitalOcean token for ``Sandbox.create(client=...)``.

    ``token_secret`` is the DigitalOcean API token; ``token_id`` is ignored.
    """

    def __init__(
        self,
        token_id: Optional[str] = None,
        token_secret: Optional[str] = None,
        *,
        do_api_url: Optional[str] = None,
        size: Optional[str] = None
    ) -> None:  # pylint: disable=super-init-not-called
        self._conn: Dict[str, Any] = {
            "token": token_secret,
            "api_url": do_api_url,
            "size": size,
        }

    def _from_credentials_sync(cls, token_id: str, token_secret: str) -> "Client":  # type: ignore[misc]  # pylint: disable=no-self-argument
        return cls(token_id, token_secret)

    async def _from_credentials_aio(cls, token_id: str, token_secret: str) -> "Client":  # type: ignore[misc]  # pylint: disable=no-self-argument
        return cls(token_id, token_secret)

    from_credentials = ModalMethod(
        _from_credentials_sync, _from_credentials_aio, "classmethod"
    )

    def close(self) -> None:
        """Nothing to close: each call manages its own connection."""


class ModalClient(Client):
    """Binds a DigitalOcean token once, like ``SandboxClient``, with Modal's names.

    ``token_secret`` is the DigitalOcean API token (default
    ``DIGITALOCEAN_ACCESS_TOKEN``; ``MODAL_TOKEN_*`` is never read). ``token_id`` is
    ignored. ``do_api_url`` and ``size`` are DigitalOcean extras: another API
    origin, and the default size slug when ``cpu``/``memory`` are not given.

    .. code-block:: python

        client = ModalClient(token_secret=token)
        sb = client.Sandbox.create(image=client.Image.debian_slim())
    """

    def __init__(
        self,
        token_id: Optional[str] = None,
        token_secret: Optional[str] = None,
        *,
        do_api_url: Optional[str] = None,
        size: Optional[str] = None
    ) -> None:
        super().__init__(token_id, token_secret, do_api_url=do_api_url, size=size)
        defaults = dict(self._conn)
        #: ``Sandbox`` with this client's token filled in.
        self.Sandbox = type(
            "Sandbox", (Sandbox,), {"_defaults": defaults}
        )  # pylint: disable=invalid-name
        self.App = App  # pylint: disable=invalid-name
        self.Image = Image  # pylint: disable=invalid-name
        self.Secret = Secret  # pylint: disable=invalid-name
        #: Modal's ``Volume`` (every method raises ``SandboxNotImplementedError``).
        self.Volume = _m.Volume  # pylint: disable=invalid-name


_HAND_WRITTEN = {
    "App",
    "Client",
    "ContainerProcess",
    "Image",
    "Sandbox",
    "Secret",
    "StreamReader",
    "StreamWriter",
    "StreamType",
}

# Everything else Modal's sandbox API exports is the generated signature mirror.
for _name, _value in vars(_m).items():
    if _name[:1].isupper() and _name not in _HAND_WRITTEN and _name not in globals():
        globals()[_name] = _value
del _name, _value
