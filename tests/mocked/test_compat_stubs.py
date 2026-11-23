# pylint: disable=missing-function-docstring,protected-access
"""Every compat method the Sandboxes API cannot serve raises ``SandboxNotImplementedError``.

Table-driven: walks the public classes of each compat package, finds the methods
that are still the generated stub (not overridden by a hand-written class), calls
each with placeholder arguments, and checks the error names ``Class.method``.
"""

import asyncio
import importlib
import inspect
import subprocess
import sys

import pytest

from pydo.sandbox import SandboxError, SandboxNotImplementedError
from pydo.sandbox.compat._base import Mirror, ModalMethod

PACKAGES = [
    ("pydo.sandbox.compat.e2b", "E2B"),
    ("pydo.aio.sandbox.compat.e2b", "E2B"),
    ("pydo.sandbox.compat.daytona", "Daytona"),
    ("pydo.aio.sandbox.compat.daytona", "Daytona"),
    ("pydo.sandbox.compat.daytona.v2", "Daytona"),
    ("pydo.aio.sandbox.compat.daytona.v2", "Daytona"),
    ("pydo.sandbox.compat.modal", "Modal"),
]

MIRRORS = [
    "pydo.sandbox.compat.e2b._mirror",
    "pydo.sandbox.compat.daytona._mirror_v0",
    "pydo.sandbox.compat.daytona._mirror_v2",
    "pydo.sandbox.compat.modal._mirror",
]


def placeholders(func):
    """``None`` for every required parameter, so the call reaches the stub body."""
    args, kwargs = [], {}
    for name, param in inspect.signature(func).parameters.items():
        if name in ("self", "cls"):
            continue
        if param.default is not inspect.Parameter.empty or param.kind in (
            param.VAR_POSITIONAL,
            param.VAR_KEYWORD,
        ):
            continue
        if param.kind is param.KEYWORD_ONLY:
            kwargs[name] = None
        else:
            args.append(None)
    return args, kwargs


def run(call):
    result = call()
    if inspect.iscoroutine(result):
        # A private loop: asyncio.run() would leave the thread with no current
        # loop, which breaks older tests that call asyncio.get_event_loop().
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(result)
        finally:
            loop.close()
    return result


def stub_owner(cls, name):
    """The class in ``cls``'s MRO that defines ``name``."""
    for klass in cls.__mro__:
        if name in klass.__dict__:
            return klass
    return None


def stubs_of(package):
    module = importlib.import_module(package)
    for cls_name in sorted(vars(module)):
        cls = getattr(module, cls_name)
        if not (inspect.isclass(cls) and issubclass(cls, Mirror)) or cls is Mirror:
            continue
        for mirror_cls in cls.__mro__:
            if not (mirror_cls.__module__.rsplit(".", 1)[-1].startswith("_mirror")):
                continue
            for name, value in sorted(mirror_cls.__dict__.items()):
                if name.startswith("_") and not isinstance(value, ModalMethod):
                    continue
                if name.startswith("_") and not isinstance(value, ModalMethod):
                    continue
                owner = stub_owner(cls, name)
                if owner is mirror_cls:
                    yield cls, mirror_cls, name, value
            break


def cases():
    seen = set()
    for package, label in PACKAGES:
        for cls, mirror_cls, name, value in stubs_of(package):
            key = (mirror_cls.__module__, mirror_cls.__name__, name)
            if key in seen:
                continue
            seen.add(key)
            yield pytest.param(
                cls,
                mirror_cls,
                name,
                value,
                label,
                id="%s:%s.%s" % (label, mirror_cls.__name__, name),
            )


CASES = list(cases())


def test_the_table_is_not_empty():
    assert len(CASES) > 700


@pytest.mark.parametrize("cls,mirror_cls,name,value,label", CASES)
def test_stub_raises_not_implemented_naming_the_method(
    cls, mirror_cls, name, value, label
):
    instance = object.__new__(cls)
    expected = "%s.%s" % (mirror_cls.__name__, name)
    if isinstance(value, ModalMethod):
        owner = cls if value._kind == "classmethod" else instance
        for impl in (value._sync, value._aio):
            args, kwargs = placeholders(impl)
            with pytest.raises(SandboxNotImplementedError) as err:
                run(lambda: impl(owner, *args, **kwargs))
            assert expected in str(err.value)
        return
    if isinstance(value, property):
        try:
            value.fget(instance)
        except SandboxNotImplementedError as err:
            assert expected in str(err)
        return
    raw = value
    owner = instance
    if isinstance(value, classmethod):
        raw, owner = value.__func__, cls
    elif isinstance(value, staticmethod):
        raw, owner = value.__func__, None
    args, kwargs = placeholders(raw)
    call = (
        (lambda: raw(*args, **kwargs))
        if owner is None
        else (lambda: raw(owner, *args, **kwargs))
    )
    with pytest.raises(SandboxNotImplementedError) as err:
        run(call)
    assert expected in str(err.value)
    assert "is not implemented on DigitalOcean Sandboxes yet" in str(err.value)


def test_the_error_is_a_sandbox_error_and_a_not_implemented_error():
    err = SandboxNotImplementedError("E2B.Filesystem.read", "the file APIs")
    assert isinstance(err, SandboxError) and isinstance(err, NotImplementedError)
    assert err.feature == "E2B.Filesystem.read" and err.needs == "the file APIs"
    assert str(err) == (
        "E2B.Filesystem.read is not implemented on DigitalOcean Sandboxes yet: needs the file APIs"
    )


def test_a_not_applicable_option_says_so_and_is_not_promised_for_later():
    err = SandboxNotImplementedError(
        "E2B.Sandbox.create(domain=...)", reason="E2B's servers are not used"
    )
    assert "not supported on DigitalOcean Sandboxes" in str(err) and "yet" not in str(
        err
    )


@pytest.mark.parametrize("mirror", MIRRORS)
def test_every_mirror_names_its_vendor_version(mirror):
    module = importlib.import_module(mirror)
    assert module.VENDOR_VERSION.split()[0] in ("e2b", "daytona", "modal")
    assert any(ch.isdigit() for ch in module.VENDOR_VERSION)


def test_import_pydo_does_not_load_the_compat_clients():
    code = (
        "import sys, pydo;"
        "assert not any(m.startswith('pydo.sandbox.compat') or m.startswith('pydo.aio.sandbox.compat') for m in sys.modules), 'compat loaded';"
        "import pydo.sandbox;"
        "assert not any('compat' in m for m in sys.modules), 'compat loaded by pydo.sandbox'"
    )
    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr


def test_the_compat_clients_load_lazily_from_the_package():
    from pydo.sandbox import compat  # pylint: disable=import-outside-toplevel

    assert compat.E2bClient.__name__ == "E2bClient"
    assert compat.DaytonaClient.__name__ == "DaytonaClient"
    assert compat.ModalClient.__name__ == "ModalClient"
    with pytest.raises(AttributeError):
        compat.Nope  # pylint: disable=pointless-statement
