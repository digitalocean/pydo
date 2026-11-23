# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async migration-only clients: E2B, Modal and Daytona names over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. The async twins of
:mod:`pydo.sandbox.compat`: ``E2bClient`` (``AsyncSandbox``), ``DaytonaClient``
(``AsyncDaytona``) and ``ModalClient`` (whose ``.aio`` calls run here). Loaded on
first use, never on ``import pydo``.
"""

from typing import Any

_LAZY = {
    "E2bClient": ("e2b", "E2bClient"),
    "DaytonaClient": ("daytona", "AsyncDaytonaClient"),
    "ModalClient": ("modal", "ModalClient"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError("module %r has no attribute %r" % (__name__, name))
    import importlib  # pylint: disable=import-outside-toplevel

    return getattr(importlib.import_module("." + target[0], __name__), target[1])


__all__ = sorted(_LAZY)
