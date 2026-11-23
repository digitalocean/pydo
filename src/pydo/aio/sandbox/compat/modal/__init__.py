# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Migrating from Modal (async): Modal's ``.aio`` calls over DigitalOcean Sandboxes.

Hand-written; preserved across ``make generate``. Modal has one ``Sandbox`` class
with a blocking and an ``.aio`` form of each method, so there is no separate async
class to mirror: this module re-exports :mod:`pydo.sandbox.compat.modal`, whose
``.aio`` methods run on the asynchronous Sandboxes SDK (``pydo.aio``).

.. code-block:: python

    import pydo.aio.sandbox.compat.modal as modal

    sb = await modal.Sandbox.create.aio(image=modal.Image.debian_slim())
    p = await sb.exec.aio("echo", "hi")
    print(await p.stdout.read.aio())
    await sb.terminate.aio()
"""

from pydo.sandbox.compat.modal import *  # noqa: F401,F403  pylint: disable=wildcard-import,unused-wildcard-import
from pydo.sandbox.compat.modal import ModalClient  # noqa: F401
