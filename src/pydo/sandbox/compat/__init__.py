# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Migration-only clients: E2B, Modal and Daytona names over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. Each client keeps its platform's
public names and signatures and calls the DigitalOcean Sandboxes SDK underneath, so
code written for another sandbox platform runs after an import swap:

.. code-block:: python

    from pydo.sandbox.compat.e2b import Sandbox          # was: from e2b import Sandbox
    from pydo.sandbox.compat.daytona import Daytona      # was: from daytona import Daytona
    import pydo.sandbox.compat.modal as modal            # was: import modal

Whatever the Sandboxes API cannot do yet (files, PTY, ports, volumes, lifetime
timeouts, metadata) keeps the platform's signature and raises
:class:`~pydo.sandbox.errors.SandboxNotImplementedError`; wire those up in the
native :class:`~pydo.sandbox.SandboxClient` first, then here.

The clients load on first use, never on ``import pydo``. The async twins are in
:mod:`pydo.aio.sandbox.compat`.
"""

from typing import Any

_LAZY = {
    "E2bClient": ("e2b", "E2bClient"),
    "DaytonaClient": ("daytona", "DaytonaClient"),
    "ModalClient": ("modal", "ModalClient"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError("module %r has no attribute %r" % (__name__, name))
    import importlib  # pylint: disable=import-outside-toplevel

    return getattr(importlib.import_module("." + target[0], __name__), target[1])


__all__ = sorted(_LAZY)
