# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""A method callable on a sandbox, or on the class with a sandbox id.

``sandbox.kill()`` acts on that sandbox; ``Sandbox.kill(sandbox_id)`` acts on
the sandbox with that id, without fetching it first.
"""

import functools
from typing import Any, Callable, Optional


class by_id_or_self:  # pylint: disable=invalid-name,too-few-public-methods
    """Descriptor choosing between an instance method and a by-id class method."""

    def __init__(self, on_instance: Callable[..., Any]) -> None:
        self._on_instance = on_instance
        self._by_id: Optional[Callable[..., Any]] = None
        functools.update_wrapper(self, on_instance)

    def by_id(self, func: Callable[..., Any]) -> "by_id_or_self":
        """Registers the implementation used when called on the class."""
        self._by_id = func
        return self

    def __get__(self, obj: Any, owner: Any = None) -> Callable[..., Any]:
        if obj is not None:
            return functools.partial(self._on_instance, obj)
        assert self._by_id is not None
        return functools.partial(self._by_id, owner)
