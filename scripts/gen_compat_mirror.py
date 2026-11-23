#!/usr/bin/env python3
"""Generates the signature mirrors of the migration-only compat clients.

The compat clients (``pydo.sandbox.compat.{e2b,daytona,modal}``) keep the public
names and signatures of the E2B, Daytona and Modal Python SDKs. Writing a few
thousand signatures by hand would drift and typo, so this script reads the
vendor packages as source text (``ast``; nothing is imported or run) and writes
one ``_mirror.py`` per vendor: every public class, with every public method
stubbed to raise ``SandboxNotImplementedError``. The hand-written clients
subclass the mirror classes and override the methods that map onto the
DigitalOcean Sandboxes API.

Only names, parameters, defaults and field names are copied: no vendor code.

Usage (vendor packages unpacked from their wheels into one directory each):

    python3 scripts/gen_compat_mirror.py --e2b DIR --daytona DIR --modal DIR

Re-run it after bumping a matched vendor version; the diff of ``_mirror.py``
shows exactly which signatures moved.
"""

from __future__ import annotations

import argparse
import ast
import glob
import keyword
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class Source:
    """One vendor file and the classes taken from it ("*" takes every public class)."""

    path: str
    classes: object = "*"


@dataclass
class Target:
    platform: str
    root_arg: str
    out: str
    version: str
    docs: str
    sources: List[Source]
    skip: set = field(default_factory=set)
    # (class regex, method regex) -> what the DigitalOcean API lacks
    needs: List[Tuple[str, str, str]] = field(default_factory=list)
    # vendor class name -> mirror class name
    rename: Dict[str, str] = field(default_factory=dict)
    modal_specs: bool = False


E2B_NEEDS = [
    (
        r"Filesystem|AsyncFilesystem|WatchHandle|AsyncWatchHandle|Volume|AsyncVolume|FileStreamReader",
        r".*",
        "the file and volume APIs",
    ),
    (r"Pty|AsyncPty", r".*", "a PTY (interactive terminal) API"),
    (r"Git|AsyncGit", r".*", "git helpers (not part of the Sandboxes API)"),
    (r"Secret|AsyncSecret", r".*", "a secrets API"),
    (
        r".*",
        r"get_host|get_url|download_url|upload_url",
        "ports and tunnels, and file transfer APIs",
    ),
    (
        r".*",
        r"set_timeout|get_info|get_full_info",
        "a sandbox lifetime and metadata API",
    ),
    (r".*", r"get_metrics|get_mcp_token", "a metrics or MCP gateway API"),
    (r".*", r"update_network", "an egress policy update API"),
    (r".*", r"fork", "a sandbox fork API"),
    (
        r"Template.*|Async(Template).*",
        r".*",
        "template builds from instructions (the DigitalOcean API builds a template from an OCI image)",
    ),
    (r".*Paginator", r".*", "a paginator over this resource"),
    (r".*", r".*", "this API"),
]

DAYTONA_NEEDS = [
    (r".*(FileSystem|FileSystemService|WatchHandle).*", r".*", "the file APIs"),
    (r".*(Git|GitService).*", r".*", "git helpers (not part of the Sandboxes API)"),
    (r".*(LspServer|Lsp).*", r".*", "a language server API"),
    (r".*(CodeInterpreter|Interpreter).*", r".*", "a code interpreter API"),
    (
        r".*(ComputerUse|Mouse|Keyboard|Screenshot|Display|Recording|Accessibility|A11y|Screen|Addon).*",
        r".*",
        "a computer use (desktop) API",
    ),
    (r".*(Volume).*", r".*", "a volumes API"),
    (r".*(Ports|Pty).*", r".*", "a ports, tunnels or PTY API"),
    (r".*(Secret).*", r".*", "a secrets API"),
    (r".*(Image|Docker).*", r".*", "image builds from instructions"),
    (r".*(WarmPool|Reservation|MacModels).*", r".*", "warm pools or reservations"),
    (
        r".*",
        r"get_preview_link|get_signed_preview_url|expire_signed_preview_url|create_ssh_access|revoke_ssh_access|validate_ssh_access|get_user_home_dir|get_work_dir|set_labels|set_autostop_interval|set_auto_archive_interval|set_auto_delete_interval|archive|recover|refresh_data|refresh_activity|fork|resize|wait_for_resize_complete",
        "a sandbox settings, preview or lifecycle API",
    ),
    (r".*", r".*", "this API"),
]

MODAL_NEEDS = [
    (r".*(Filesystem|FileIO).*", r".*", "the file APIs"),
    (r".*", r"tunnels|create_connect_token", "a ports and tunnels API"),
    (
        r".*",
        r".*snapshot.*|.*from_snapshot|mount_image|unmount_image",
        "a snapshot restore API",
    ),
    (r".*(Volume|CloudBucketMount|NetworkFileSystem).*", r".*", "a volumes API"),
    (
        r"Image",
        r".*",
        "image builds from instructions (create a template from an OCI image and use Image.from_registry)",
    ),
    (
        r"App",
        r".*",
        "Modal apps, functions and deployments (an App only groups sandboxes here)",
    ),
    (r"Secret", r".*", "a secrets store (use Secret.from_dict)"),
    (
        r".*(Dict|Queue|Function|Cls|Cron|Period|Retries|Proxy|Server|Client).*",
        r".*",
        "this Modal product (outside the Sandbox API)",
    ),
    (
        r".*",
        r"set_tags|get_tags|_experimental_set_name|set_outbound.*|update_outbound.*",
        "a tags or egress policy API",
    ),
    (
        r".*",
        r"logs|_experimental_stats|reload_volumes",
        "a logs, stats or volume reload API",
    ),
    (r".*", r".*", "this API"),
]

DAYTONA_V0_SYNC = [
    "Daytona",
    "Sandbox",
    "SandboxNode",
    "SandboxNodeProcess",
    "SandboxNodeFileSystem",
    "SandboxNodeCollection",
]
TARGETS = [
    Target(
        platform="e2b",
        root_arg="e2b",
        out="src/pydo/sandbox/compat/e2b/_mirror.py",
        version="e2b 2.64.0",
        docs="https://docs.e2b.dev/client",
        sources=[
            Source("e2b/sandbox/main.py", ["SandboxBase"]),
            Source("e2b/sandbox_sync/main.py", ["Sandbox"]),
            Source("e2b/sandbox_async/main.py", ["AsyncSandbox"]),
            Source("e2b/sandbox_sync/sandbox_api.py", ["SandboxApi"]),
            Source(
                "e2b/sandbox_async/sandbox_api.py", [("SandboxApi", "AsyncSandboxApi")]
            ),
            Source("e2b/sandbox_sync/commands/command.py", ["Commands"]),
            Source(
                "e2b/sandbox_async/commands/command.py", [("Commands", "AsyncCommands")]
            ),
            Source("e2b/sandbox_sync/commands/command_handle.py", ["CommandHandle"]),
            Source(
                "e2b/sandbox_async/commands/command_handle.py", ["AsyncCommandHandle"]
            ),
            Source(
                "e2b/sandbox_async/commands/command_input_handle.py",
                ["AsyncCommandInputHandle"],
            ),
            Source("e2b/sandbox_sync/commands/pty.py", ["Pty"]),
            Source("e2b/sandbox_async/commands/pty.py", [("Pty", "AsyncPty")]),
            Source("e2b/sandbox_sync/filesystem/filesystem.py", ["Filesystem"]),
            Source(
                "e2b/sandbox_async/filesystem/filesystem.py",
                [("Filesystem", "AsyncFilesystem")],
            ),
            Source("e2b/sandbox_sync/filesystem/watch_handle.py", ["WatchHandle"]),
            Source(
                "e2b/sandbox_async/filesystem/watch_handle.py", ["AsyncWatchHandle"]
            ),
            Source("e2b/sandbox_sync/git.py", ["Git"]),
            Source("e2b/sandbox_async/git.py", [("Git", "AsyncGit")]),
            Source(
                "e2b/sandbox_sync/paginator.py",
                ["SandboxPaginator", "SnapshotPaginator"],
            ),
            Source(
                "e2b/sandbox_async/paginator.py",
                ["AsyncSandboxPaginator", "AsyncSnapshotPaginator"],
            ),
            Source("e2b/paginator.py", ["PaginatorBase"]),
            Source("e2b/template_sync/main.py", ["Template"]),
            Source("e2b/template_async/main.py", ["AsyncTemplate"]),
            Source("e2b/template_sync/paginator.py", ["TemplatePaginator"]),
            Source("e2b/template_async/paginator.py", ["AsyncTemplatePaginator"]),
            Source(
                "e2b/template/main.py",
                ["TemplateBase", "TemplateBuilder", "TemplateFinal"],
            ),
            Source("e2b/template/types.py"),
            Source("e2b/volume/volume_sync.py", ["Volume"]),
            Source("e2b/volume/volume_async.py", ["AsyncVolume"]),
            Source("e2b/volume/types.py"),
            Source("e2b/secret/secret_sync.py", ["Secret", "SecretPaginator"]),
            Source(
                "e2b/secret/secret_async.py", ["AsyncSecret", "AsyncSecretPaginator"]
            ),
            Source("e2b/secret/types.py"),
            Source("e2b/sandbox/sandbox_api.py"),
            Source("e2b/sandbox/network.py"),
            Source("e2b/sandbox/iam.py"),
            Source(
                "e2b/sandbox/filesystem/filesystem.py",
                [
                    "FileType",
                    "WriteInfo",
                    "EntryInfo",
                    "WriteEntry",
                    "SyncWriteEntry",
                    "AsyncWriteEntry",
                ],
            ),
            Source("e2b/sandbox/filesystem/watch_handle.py"),
            Source(
                "e2b/connection_config.py",
                ["ConnectionConfig", "ApiParams", "ApiParamsWithLogger"],
            ),
            Source("e2b/sandbox/commands/main.py", ["ProcessInfo"]),
            Source("e2b/sandbox/commands/command_handle.py", ["PtySize"]),
        ],
        skip={
            "SandboxBase",
            "ConnectionConfig",
            "PaginatorBase",
            "SandboxApi",
            "AsyncSandboxApi",
        },
        needs=E2B_NEEDS,
        rename={},
    ),
    Target(
        platform="daytona",
        root_arg="daytona",
        out="src/pydo/sandbox/compat/daytona/_mirror_v0.py",
        version="daytona 2.1.0 (v0 namespace; the legacy daytona-sdk 0.233.0 wheel has the same shapes)",
        docs="https://www.daytona.io/docs/en/python-sdk/",
        sources=[
            Source("daytona/v0/common/*.py"),
            Source("daytona/v0/_sync/*.py"),
            Source("daytona/v0/_async/*.py"),
            Source("daytona/v0/handle/*.py"),
        ],
        needs=DAYTONA_NEEDS,
    ),
    Target(
        platform="daytona",
        root_arg="daytona",
        out="src/pydo/sandbox/compat/daytona/_mirror_v2.py",
        version="daytona 2.1.0 (v2 namespace)",
        docs="https://www.daytona.io/docs/en/python-sdk/",
        sources=[
            Source("daytona/v2/_sync/*.py"),
            Source("daytona/v2/daytona.py"),
            Source("daytona/v2/sandbox.py"),
            Source("daytona/v2/filesystem.py"),
            Source("daytona/v2/git.py"),
            Source("daytona/v2/process.py"),
            Source("daytona/v2/interpreter.py"),
            Source("daytona/v2/ports.py"),
            Source("daytona/v2/services.py"),
            Source("daytona/v2/session.py"),
            Source("daytona/v2/computer_use.py"),
            Source("daytona/v2/computer_use_services.py"),
            Source("daytona/v2/docker.py"),
            Source("daytona/v2/image.py"),
            Source("daytona/v2/sandbox_volumes.py"),
            Source("daytona/v2/types.py"),
            Source("daytona/v2/build_logs.py"),
            Source("daytona/v2/computer_use_types.py"),
            Source("daytona/v2/network_policy.py"),
        ],
        needs=DAYTONA_NEEDS,
    ),
    Target(
        platform="modal",
        root_arg="modal",
        out="src/pydo/sandbox/compat/modal/_mirror.py",
        version="modal 1.6.4",
        docs="https://modal.com/docs/sdk/py/latest",
        modal_specs=True,
        sources=[
            Source(
                "modal/sandbox/sandbox.pyi",
                [
                    "Sandbox",
                    "SandboxSnapshot",
                    "SandboxFilesystem",
                    "SidecarContainer",
                    "SidecarManager",
                ],
            ),
            Source("modal/container_process.pyi", ["ContainerProcess"]),
            Source("modal/io_streams.pyi", ["StreamReader", "StreamWriter"]),
            Source("modal/app.pyi", ["App"]),
            Source("modal/image.pyi", ["Image"]),
            Source("modal/secret.pyi", ["Secret"]),
            Source("modal/volume.pyi", ["Volume"]),
            Source("modal/cloud_bucket_mount.pyi", ["CloudBucketMount"]),
            Source("modal/network_file_system.pyi", ["NetworkFileSystem"]),
            Source("modal/proxy.pyi", ["Proxy"]),
            Source("modal/client.pyi", ["Client"]),
            Source("modal/_tunnel.pyi", ["Tunnel"]),
        ],
        needs=MODAL_NEEDS,
    ),
]


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


@dataclass
class Method:
    name: str
    sig: str  # "(self, a: int = 1, *, b=None) -> T" source text
    is_async: bool
    kind: str  # "method" | "classmethod" | "staticmethod" | "property" | "dual"
    doc_sigs: List[str] = field(default_factory=list)
    returns: str = ""


@dataclass
class Klass:
    name: str
    bases: List[str]
    kind: str  # "plain" | "enum" | "typeddict" | "model" | "exception"
    methods: Dict[str, Method]
    fields: List[Tuple[str, str, str]]  # name, annotation, default source
    members: List[Tuple[str, str]]  # enum members
    total: Optional[str] = None
    source: str = ""


def _fmt_args(a: ast.arguments, drop_self: bool = False) -> str:
    parts: List[str] = []
    pos = a.posonlyargs + a.args
    defaults = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    for i, (x, d) in enumerate(zip(pos, defaults)):
        s = x.arg
        if x.annotation is not None:
            s += ": " + ast.unparse(x.annotation)
        if d is not None:
            s += " = " + ast.unparse(d)
        parts.append(s)
        if a.posonlyargs and i == len(a.posonlyargs) - 1:
            parts.append("/")
    if a.vararg:
        s = "*" + a.vararg.arg
        if a.vararg.annotation is not None:
            s += ": " + ast.unparse(a.vararg.annotation)
        parts.append(s)
    elif a.kwonlyargs:
        parts.append("*")
    for x, d in zip(a.kwonlyargs, a.kw_defaults):
        s = x.arg
        if x.annotation is not None:
            s += ": " + ast.unparse(x.annotation)
        if d is not None:
            s += " = " + ast.unparse(d)
        parts.append(s)
    if a.kwarg:
        s = "**" + a.kwarg.arg
        if a.kwarg.annotation is not None:
            s += ": " + ast.unparse(a.kwarg.annotation)
        parts.append(s)
    return ", ".join(parts)


def _decorator_names(fn) -> List[str]:
    out = []
    for d in fn.decorator_list:
        node = d.func if isinstance(d, ast.Call) else d
        out.append(ast.unparse(node).split(".")[-1])
    return out


def _method_from(fn) -> Optional[Method]:
    decs = _decorator_names(fn)
    if "overload" in decs:
        return None
    name = fn.name
    if name.startswith("_") and name not in (
        "__enter__",
        "__exit__",
        "__aenter__",
        "__aexit__",
        "__iter__",
        "__aiter__",
        "__next__",
        "__anext__",
        "__call__",
    ):
        return None
    kind = "method"
    if "class_method_variant" in decs:
        kind = "dual"
    elif "classmethod" in decs:
        kind = "classmethod"
    elif "staticmethod" in decs:
        kind = "staticmethod"
    elif "property" in decs:
        kind = "property"
    sig = "(" + _fmt_args(fn.args) + ")"
    ret = ast.unparse(fn.returns) if fn.returns is not None else ""
    return Method(name, sig, isinstance(fn, ast.AsyncFunctionDef), kind, [], ret)


def _class_kind(node: ast.ClassDef) -> str:
    bases = [ast.unparse(b) for b in node.bases]
    joined = " ".join(bases)
    decs = " ".join(ast.unparse(d) for d in node.decorator_list)
    if re.search(r"\bEnum\b|\bIntEnum\b|\bStrEnum\b", joined):
        return "enum"
    if "TypedDict" in joined:
        return "typeddict"
    if re.search(r"Exception|Error", joined) or node.name.endswith(
        ("Exception", "Error")
    ):
        return "exception"
    if "dataclass" in decs or "BaseModel" in joined or "Model" in joined:
        return "model"
    return "plain"


def _modal_spec_methods(node: ast.ClassDef) -> Dict[str, Method]:
    """Modal ships synchronicity stubs: ``attr: __name_spec`` plus a nested spec class."""
    specs: Dict[str, ast.ClassDef] = {
        c.name: c for c in node.body if isinstance(c, ast.ClassDef)
    }
    out: Dict[str, Method] = {}
    for m in node.body:
        if isinstance(m, ast.AnnAssign) and isinstance(m.target, ast.Name):
            ann = ast.unparse(m.annotation)
            mm = re.search(r"(__\w*_spec)\b", ann)
            if mm and mm.group(1) in specs:
                spec = specs[mm.group(1)]
                calls = [
                    f
                    for f in spec.body
                    if isinstance(f, ast.FunctionDef) and f.name == "__call__"
                ]
                aio = [
                    f
                    for f in spec.body
                    if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and f.name == "aio"
                ]
                if not calls:
                    continue
                call = calls[0]
                args = ast.parse("def f(): pass").body[0].args
                call_args = call.args
                # drop the leading `self` and the positional-only marker the stub uses for it
                cargs = ast.arguments(
                    posonlyargs=(
                        [x for x in call_args.posonlyargs[1:]]
                        if call_args.posonlyargs
                        else []
                    ),
                    args=(
                        call_args.args[1:]
                        if not call_args.posonlyargs
                        else call_args.args
                    ),
                    vararg=call_args.vararg,
                    kwonlyargs=call_args.kwonlyargs,
                    kw_defaults=call_args.kw_defaults,
                    kwarg=call_args.kwarg,
                    defaults=call_args.defaults,
                )
                cls_var = "ClassVar" in ann
                sig = "(" + _fmt_args(cargs) + ")"
                meth = Method(
                    m.target.id,
                    sig,
                    False,
                    "classmethod" if cls_var else "method",
                    [],
                    ast.unparse(call.returns) if call.returns else "",
                )
                if aio:
                    a = aio[0]
                    aargs = a.args
                    acargs = ast.arguments(
                        posonlyargs=aargs.posonlyargs[1:] if aargs.posonlyargs else [],
                        args=aargs.args[1:] if not aargs.posonlyargs else aargs.args,
                        vararg=aargs.vararg,
                        kwonlyargs=aargs.kwonlyargs,
                        kw_defaults=aargs.kw_defaults,
                        kwarg=aargs.kwarg,
                        defaults=aargs.defaults,
                    )
                    meth.doc_sigs = ["(" + _fmt_args(acargs) + ")"]
                out[meth.name] = meth
        elif isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
            meth = _method_from(m)
            if meth and meth.name not in out:
                out[meth.name] = meth
    return out


def parse_classes(path: str, modal: bool) -> Dict[str, Klass]:
    tree = ast.parse(open(path, encoding="utf-8").read())
    out: Dict[str, Klass] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
            continue
        kind = _class_kind(node)
        bases = [ast.unparse(b) for b in node.bases]
        methods: Dict[str, Method] = {}
        fields: List[Tuple[str, str, str]] = []
        members: List[Tuple[str, str]] = []
        total = None
        for kw in node.keywords:
            if kw.arg == "total":
                total = ast.unparse(kw.value)
        if modal:
            methods = _modal_spec_methods(node)
        for m in node.body:
            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and not modal:
                meth = _method_from(m)
                if meth:
                    methods[meth.name] = meth
            elif isinstance(m, ast.AnnAssign) and isinstance(m.target, ast.Name):
                if m.target.id.startswith("_") and not modal:
                    continue
                if not m.target.id.startswith("_"):
                    default = ""
                    if m.value is not None:
                        default = ast.unparse(m.value)
                    fields.append((m.target.id, ast.unparse(m.annotation), default))
            elif isinstance(m, ast.Assign) and kind == "enum":
                for t in m.targets:
                    if isinstance(t, ast.Name) and not t.id.startswith("_"):
                        members.append((t.id, ast.unparse(m.value)))
        out[node.name] = Klass(node.name, bases, kind, methods, fields, members, total)
    return out


def module_constants(path: str) -> Dict[str, str]:
    """Simple ``NAME = <literal>`` assignments, so defaults that name them still resolve."""
    tree = ast.parse(open(path, encoding="utf-8").read())
    out: Dict[str, str] = {}
    for node in tree.body:
        value = None
        name = None
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            name, value = node.targets[0].id, node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            name, value = node.target.id, node.value
        if name and value is not None and _is_literal(value):
            out[name] = ast.unparse(value)
    return out


def _is_literal(node) -> bool:
    try:
        ast.literal_eval(node)
        return True
    except Exception:  # pylint: disable=broad-except
        return False


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------

BUILTIN_NAMES = (
    set(dir(__builtins__)) if not isinstance(__builtins__, dict) else set(__builtins__)
)
TYPING_NAMES = {
    "Any",
    "Optional",
    "Union",
    "List",
    "Dict",
    "Tuple",
    "Set",
    "Callable",
    "Iterable",
    "Iterator",
    "AsyncIterator",
    "Generator",
    "AsyncGenerator",
    "Awaitable",
    "Literal",
    "Mapping",
    "Sequence",
    "TypeVar",
    "Generic",
    "ClassVar",
    "Type",
    "IO",
    "BinaryIO",
    "TextIO",
    "Coroutine",
    "Protocol",
    "NamedTuple",
    "Final",
    "Self",
    "Unpack",
    "Required",
    "NotRequired",
    "TypedDict",
    "overload",
    "cast",
    "Awaitable",
    "AsyncContextManager",
    "ContextManager",
}


def _names_in(expr: str) -> set:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return set()
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}


def _safe_default_sig(sig: str, consts: Dict[str, str], extra: Dict[str, str]) -> str:
    """Replace any default that names something the mirror module will not define."""
    try:
        fn = ast.parse("def f" + sig + ": pass").body[0]
    except SyntaxError:
        return "(*args, **kwargs)"
    a = fn.args

    def fix(d):
        if d is None:
            return d
        names = _names_in(ast.unparse(d))
        bad = {
            n
            for n in names
            if n not in BUILTIN_NAMES
            and n not in TYPING_NAMES
            and n not in {"None", "True", "False"}
        }
        if not bad:
            return d
        if all(n in consts for n in bad):
            extra.update({n: consts[n] for n in bad})
            return d
        return ast.Constant(value=None)

    a.defaults = [fix(d) for d in a.defaults]
    a.kw_defaults = [fix(d) for d in a.kw_defaults]
    return "(" + _fmt_args(a) + ")"


def _needs(rules, cls: str, method: str) -> str:
    for c, m, text in rules:
        if re.fullmatch(c, cls) and re.fullmatch(m, method):
            return text
    return "this API"


def _py_name(name: str) -> str:
    return name + "_" if keyword.iskeyword(name) else name


def emit_target(t: Target, roots: Dict[str, str]) -> str:
    root = roots[t.root_arg]
    pool: Dict[str, Klass] = {}
    order: List[str] = []
    consts: Dict[str, str] = {}
    files: List[Tuple[Source, Dict[str, Klass]]] = []
    expanded: List[Source] = []
    for src in t.sources:
        if "*" in src.path:
            for hit in sorted(glob.glob(os.path.join(root, src.path))):
                if os.path.basename(hit) == "__init__.py":
                    continue
                expanded.append(Source(os.path.relpath(hit, root), src.classes))
        else:
            expanded.append(src)
    for src in expanded:
        path = os.path.join(root, src.path)
        # Modal ships .pyi stubs for the public API
        if not os.path.exists(path) and os.path.exists(path + "i"):
            path += "i"
        if not os.path.exists(path):
            print("missing", path, file=sys.stderr)
            continue
        classes = parse_classes(path, t.modal_specs)
        consts.update(module_constants(path))
        files.append((src, classes))
        for name, k in classes.items():
            pool.setdefault(name, k)
    chosen: List[Tuple[str, Klass]] = []
    seen = set()
    for src, classes in files:
        wanted = list(classes) if src.classes == "*" else src.classes
        for w in wanted:
            vendor, mirror = (w, w) if isinstance(w, str) else w
            vendor_cls = classes.get(vendor)
            if vendor_cls is None:
                print("class not found", src.path, vendor, file=sys.stderr)
                continue
            mirror = t.rename.get(mirror, mirror)
            if mirror in seen or vendor in t.skip and mirror == vendor:
                continue
            seen.add(mirror)
            chosen.append((mirror, vendor_cls))
    mirror_names = {m for m, _ in chosen}
    chosen = _toposort(chosen, mirror_names)
    extra_consts: Dict[str, str] = {}
    lines: List[str] = []
    for mirror, k in chosen:
        lines.extend(
            _emit_class(t, mirror, k, pool, mirror_names, consts, extra_consts)
        )
    head = [
        f'"""Signature mirror of {t.version} ({t.docs}). GENERATED by scripts/gen_compat_mirror.py: do not edit."""',
        "",
        "# pylint: skip-file",
        "# type: ignore",
        "# flake8: noqa",
        "from __future__ import annotations",
        "",
        "import datetime",
        "import enum",
        "import logging",
        "import os",
        "import pathlib",
        "from typing import *  # noqa: F401,F403",
        "",
        "from pydo.sandbox.compat._base import Mirror, Model, ModalMethod, mirror_typeddict  # noqa: F401",
        "",
        f"PLATFORM = {t.platform!r}",
        f"VENDOR_VERSION = {t.version!r}",
        "",
    ]
    for name, value in sorted(extra_consts.items()):
        head.append(f"{name} = {value}")
    head.append("")
    body = "\n".join(lines)
    # shared names the mirror classes refer to in annotations only
    return "\n".join(head) + body + "\n"


def _toposort(chosen, mirror_names):
    """Bases first: a class statement needs its base defined above it."""
    by_name = dict(chosen)
    done: List[Tuple[str, Klass]] = []
    placed = set()

    def place(name: str, stack=()):
        if name in placed or name not in by_name:
            return
        for b in by_name[name].bases:
            base = re.sub(r"\[.*\]", "", b).split(".")[-1]
            if base in mirror_names and base != name and base not in stack:
                place(base, stack + (name,))
        placed.add(name)
        done.append((name, by_name[name]))

    for name, _ in chosen:
        place(name)
    return done


def _collect_methods(k: Klass, pool: Dict[str, Klass], seen=None) -> Dict[str, Method]:
    seen = seen or set()
    out: Dict[str, Method] = {}
    for b in k.bases:
        base = re.sub(r"\[.*\]", "", b).split(".")[-1]
        if base in pool and base not in seen:
            seen.add(base)
            out.update(_collect_methods(pool[base], pool, seen))
    out.update(k.methods)
    return out


def _collect_fields(k: Klass, pool: Dict[str, Klass], seen=None):
    seen = seen or set()
    out: Dict[str, Tuple[str, str]] = {}
    for b in k.bases:
        base = re.sub(r"\[.*\]", "", b).split(".")[-1]
        if base in pool and base not in seen:
            seen.add(base)
            out.update(
                {n: (a, d) for n, a, d in _collect_fields(pool[base], pool, seen)}
            )
    out.update({n: (a, d) for n, a, d in k.fields})
    return [(n, a, d) for n, (a, d) in out.items()]


def _emit_class(
    t: Target, mirror: str, k: Klass, pool, mirror_names, consts, extra_consts
) -> List[str]:
    out: List[str] = []
    bases = []
    for b in k.bases:
        base = re.sub(r"\[.*\]", "", b).split(".")[-1]
        if base in mirror_names and base != mirror:
            bases.append(base)
    if k.kind == "enum":
        enum_base = "enum.Enum"
        if any("str" in b for b in k.bases):
            enum_base = "str, enum.Enum"
        out.append(f"class {mirror}({enum_base}):")
        if not k.members:
            out.append("    pass")
        for n, v in k.members:
            out.append(f"    {_py_name(n)} = {v}")
        out.append("")
        return out
    if k.kind == "typeddict":
        fields = _collect_fields(k, pool)
        out.append(f"{mirror} = mirror_typeddict(")
        out.append(f"    {mirror!r},")
        out.append("    {" + ", ".join(f"{n!r}: {a!r}" for n, a, _ in fields) + "},")
        out.append(f"    total={k.total or 'True'},")
        out.append(")")
        out.append("")
        return out
    if k.kind == "exception":
        # exceptions are hand-written per vendor (they carry our error mapping)
        return out
    external = [
        b
        for b in k.bases
        if re.sub(r"\[.*\]", "", b).split(".")[-1] not in mirror_names
        and re.sub(r"\[.*\]", "", b).split(".")[-1]
        not in ("Generic", "Protocol", "object", "ABC", "BaseModel")
    ]
    as_model = k.kind == "model" or (k.kind == "plain" and external and not bases)
    base_list = ", ".join(bases or (["Model"] if as_model else ["Mirror"]))
    out.append(f"class {mirror}({base_list}):")
    out.append(f"    _platform = PLATFORM")
    out.append(f"    _vendor_class = {mirror!r}")
    fields = _collect_fields(k, pool)
    if as_model or fields:
        for n, a, d in fields:
            if n.startswith("_") or keyword.iskeyword(n):
                continue
            out.append(f"    {n}: {a}")
        if fields:
            out.append(
                "    _fields = ("
                + "".join(
                    f"{n!r}, "
                    for n, _, _ in fields
                    if not n.startswith("_") and not keyword.iskeyword(n)
                )
                + ")"
            )
            defaults = []
            for n, a, d in fields:
                if n.startswith("_") or keyword.iskeyword(n):
                    continue
                dv = "None"
                if d and _is_literal_expr(d):
                    dv = d
                defaults.append(f"{n!r}: {dv}")
            out.append("    _defaults = {" + ", ".join(defaults) + "}")
    methods = _collect_methods(k, pool)
    for name, m in methods.items():
        if keyword.iskeyword(name):
            continue
        sig = _safe_default_sig(m.sig, consts, extra_consts)
        needs = _needs(t.needs, mirror, name)
        qual = f"{mirror}.{name}"
        pre = "async " if m.is_async else ""
        if m.kind == "property":
            ret = f" -> {m.returns}" if m.returns else ""
            if (
                m.returns
                and re.sub(r"[^\w]", "", m.returns) in mirror_names
                and m.returns.isidentifier()
            ):
                out.append("    @property")
                out.append(f"    def {name}(self){ret}:")
                out.append(f"        return self._child({m.returns})")
            else:
                out.append("    @property")
                out.append(f"    def {name}(self){ret}:")
                out.append(f"        raise self._ni({qual!r}, {needs!r})")
            continue
        if m.kind == "dual":
            doc = m.sig.replace('"""', "'''")
            out.append(f"    def {name}(self, *args, **kwargs):")
            out.append(
                f'        """Signature: {name}{doc}; also callable on the class with a leading `sandbox_id`."""'
            )
            out.append(f"        raise self._ni({qual!r}, {needs!r})")
            continue
        ret = f" -> {m.returns}" if m.returns else ""
        sig_text = sig
        if t.modal_specs and m.kind in ("classmethod", "method") and name != "__init__":
            first = "cls" if m.kind == "classmethod" else "self"
            st = _with_first(sig, first)
            out.append(f"    def _{name}_sync{st}{ret}:")
            out.append(f"        raise {first}._ni({qual!r}, {needs!r})")
            out.append(f"    async def _{name}_aio{st}{ret}:")
            out.append(f"        raise {first}._ni({qual!r}, {needs!r})")
            out.append(
                f"    {name} = ModalMethod(_{name}_sync, _{name}_aio, {m.kind!r})"
            )
            continue
        if m.kind == "classmethod":
            first = "cls"
            sig_text = _with_first(sig, "cls")
            out.append("    @classmethod")
            out.append(f"    {pre}def {name}{sig_text}{ret}:")
            out.append(f"        raise cls._ni({qual!r}, {needs!r})")
        elif m.kind == "staticmethod":
            out.append("    @staticmethod")
            out.append(f"    {pre}def {name}{sig_text}{ret}:")
            out.append(f"        raise Mirror._ni({qual!r}, {needs!r})")
        else:
            sig_text = _with_first(sig, "self")
            out.append(f"    {pre}def {name}{sig_text}{ret}:")
            out.append(f"        raise self._ni({qual!r}, {needs!r})")
        for extra in m.doc_sigs:
            pass
    if not methods and k.kind != "model" and not fields:
        pass
    out.append("")
    return out


def _is_literal_expr(d: str) -> bool:
    try:
        ast.literal_eval(d)
        return True
    except Exception:  # pylint: disable=broad-except
        return False


def _with_first(sig: str, first: str) -> str:
    """Methods keep the vendor's own first parameter; modal's stubs drop it, so add it back."""
    inner = sig[1:-1].strip()
    if inner.startswith(("self", "cls")):
        parts = inner.split(",", 1)
        rest = parts[1].strip() if len(parts) > 1 else ""
        return "(" + first + (", " + rest if rest else "") + ")"
    return "(" + first + (", " + inner if inner else "") + ")"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e2b")
    ap.add_argument("--daytona")
    ap.add_argument("--modal")
    ap.add_argument("--only")
    args = ap.parse_args()
    roots = {"e2b": args.e2b, "daytona": args.daytona, "modal": args.modal}
    for t in TARGETS:
        if args.only and t.platform != args.only:
            continue
        if not roots.get(t.root_arg):
            print("skip", t.platform, "(no source dir)")
            continue
        text = emit_target(t, roots)
        out = os.path.join(ROOT, t.out)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote", t.out, len(text.splitlines()), "lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
