# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Shared plumbing of the migration-only compat clients.

Hand-written; preserved across ``make generate``. The generated ``_mirror.py``
modules keep another platform's public names and signatures; every method they
declare raises :class:`~pydo.sandbox.errors.SandboxNotImplementedError` until a
hand-written subclass overrides it with a call into the Sandboxes SDK.
"""

import functools
import inspect
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from ..errors import SandboxError, SandboxNotImplementedError

#: Display names used in error messages, by platform key.
LABELS = {"e2b": "E2B", "daytona": "Daytona", "modal": "Modal"}


def labelled(platform: str, qualified: str) -> str:
    """``E2B.Sandbox.create``: the platform label, once, in front of ``Class.method``."""
    label = LABELS.get(platform, "")
    if not label or qualified.startswith(label + "."):
        return qualified
    return "%s.%s" % (label, qualified)


class Mirror:
    """Base of every mirrored class: methods raise until an override implements them."""

    _platform = ""
    _vendor_class = ""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._parent = args[0] if args else None
        self._init_args = args
        self._init_kwargs = kwargs

    @classmethod
    def _ni(
        cls, feature: str, needs: Optional[str] = None
    ) -> SandboxNotImplementedError:
        """The error for ``feature`` (``Class.method``), labelled with the platform."""
        return SandboxNotImplementedError(
            labelled(getattr(cls, "_platform", ""), feature), needs
        )

    def _child(self, klass: Any) -> Any:
        """A mirrored sub-object (``sandbox.files``) that carries the owner."""
        return klass(self)


class Model(Mirror):
    """A mirrored data class: keyword or positional fields, plain attributes.

    ``_fields`` and ``_defaults`` come from the vendor class. A field that was not
    given reads as its default, or ``None``, so code that probes optional
    attributes keeps working.
    """

    _fields: Tuple[str, ...] = ()
    _defaults: Dict[str, Any] = {}

    def __init__(
        self, *args: Any, **kwargs: Any
    ) -> None:  # pylint: disable=super-init-not-called
        values = dict(zip(self._fields, args))
        for name, value in kwargs.items():
            values[name] = value
        for name in self._fields:
            if name not in values:
                values[name] = self._defaults.get(name)
        for name, value in values.items():
            setattr(self, name, value)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return None

    def __repr__(self) -> str:
        shown = ", ".join(
            "%s=%r" % (n, getattr(self, n, None)) for n in self._fields[:6]
        )
        return "%s(%s)" % (self.__class__.__name__, shown)

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and all(
            getattr(self, n, None) == getattr(other, n, None) for n in self._fields
        )

    __hash__ = None  # type: ignore[assignment]


def mirror_typeddict(name: str, fields: Mapping[str, str], total: bool = True) -> Any:
    """A ``TypedDict`` with the vendor's keys (annotations stay strings)."""
    from typing import TypedDict  # pylint: disable=import-outside-toplevel

    return TypedDict(name, dict(fields), total=total)  # type: ignore[operator]


def reject(platform: str, qualified: str, needs: str, **given: Any) -> None:
    """Raise when a caller passes an option the Sandboxes API cannot honor.

    ``given`` maps an option name to the value the caller passed; only options
    whose value is not ``None``/empty count as passed.
    """
    for option, value in given.items():
        if value is None:
            continue
        if isinstance(value, (dict, list, tuple, set)) and not value:
            continue
        raise SandboxNotImplementedError(
            "%s(%s=...)" % (labelled(platform, qualified), option), needs
        )


class ModalMethod:
    """A Modal method that exists in a blocking and an ``.aio`` form.

    Modal's client wraps one coroutine in two call styles: ``Sandbox.create(...)``
    blocks and ``await Sandbox.create.aio(...)`` awaits. This descriptor keeps
    both spellings: it binds to the instance (``kind="method"``) or to the class
    (``kind="classmethod"``) and calls the matching implementation.
    """

    def __init__(self, sync: Any, aio: Any, kind: str = "method") -> None:
        self._sync = sync
        self._aio = aio
        self._kind = kind
        self.__doc__ = getattr(sync, "__doc__", None)

    def __set_name__(self, owner: Any, name: str) -> None:
        self.__name__ = name

    def __get__(self, obj: Any, owner: Any = None) -> "_ModalBound":
        target = owner if (self._kind == "classmethod" or obj is None) else obj
        return _ModalBound(self._sync, self._aio, target)


class _ModalBound:
    def __init__(self, sync: Any, aio: Any, target: Any) -> None:
        self._s = sync
        self._a = aio
        self._t = target

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._s(self._t, *args, **kwargs)

    def aio(self, *args: Any, **kwargs: Any) -> Any:
        """The awaitable form: ``await Sandbox.create.aio(...)``."""
        return self._a(self._t, *args, **kwargs)


def translating(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Re-raise the Sandboxes SDK's typed errors as the platform's own exceptions.

    The first argument (``self`` or ``cls``) must provide ``_map_error(err)``,
    which returns the platform exception for a :class:`SandboxError`. A
    :class:`SandboxNotImplementedError` passes through untouched.
    """

    def _convert(args: Tuple[Any, ...], err: SandboxError) -> BaseException:
        mapper = getattr(args[0], "_map_error", None) if args else None
        return mapper(err) if mapper else err

    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def awrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await fn(*args, **kwargs)
            except SandboxNotImplementedError:
                raise
            except SandboxError as err:
                raise _convert(args, err) from err

        return awrapper

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except SandboxNotImplementedError:
            raise
        except SandboxError as err:
            raise _convert(args, err) from err

    return wrapper


def with_signature(stub: Callable[..., Any]) -> Callable[..., Any]:
    """Give an implementation a stub's exact signature, and bind arguments like Python does.

    ``impl(owner, args)`` receives the owner (class or instance) and a dict of
    every parameter by name, defaults applied (``*args`` arrives as a tuple under
    its own name). Calling with a parameter the stub does not have raises the
    same ``TypeError`` a real signature would. Works for sync and async impls.
    """
    sig = inspect.signature(stub)

    def decorate(impl: Callable[..., Any]) -> Callable[..., Any]:
        def bind(
            owner: Any, args: Tuple[Any, ...], kwargs: Dict[str, Any]
        ) -> Dict[str, Any]:
            bound = sig.bind(owner, *args, **kwargs)
            bound.apply_defaults()
            values = dict(bound.arguments)
            values.pop(next(iter(sig.parameters)), None)
            return values

        if inspect.iscoroutinefunction(impl):

            @functools.wraps(impl)
            async def awrapper(owner: Any, *args: Any, **kwargs: Any) -> Any:
                return await impl(owner, bind(owner, args, kwargs))

            awrapper.__signature__ = sig  # type: ignore[attr-defined]
            return awrapper

        @functools.wraps(impl)
        def wrapper(owner: Any, *args: Any, **kwargs: Any) -> Any:
            return impl(owner, bind(owner, args, kwargs))

        wrapper.__signature__ = sig  # type: ignore[attr-defined]
        return wrapper

    return decorate
