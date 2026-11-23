# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Local objects and option handling shared by the sync and async Modal compat clients."""

import enum
import hashlib
import os
from typing import Any, Dict, List, Mapping, Optional, Tuple

from ...errors import SandboxNotImplementedError
from .. import _base
from . import _mirror as _m

#: Modal's own default for ``Sandbox.create(timeout=...)``: indistinguishable from "not passed".
MODAL_DEFAULT_TIMEOUT = 300

#: The sandbox sizes ``cpu`` and ``memory`` round up to, as ``(slug, vcpus, memory_mb)``.
#: From ``doctl harness-runtime sizes list``; a withdrawn slug fails at create with the
#: API's own error listing the current ones.
SIZES = (
    ("mars-1vcpu-1gb", 1, 1024),
    ("mars-2vcpu-2gb", 2, 2048),
    ("mars-2vcpu-4gb", 2, 4096),
    ("mars-4vcpu-8gb", 4, 8192),
    ("mars-16vcpu-32gb", 16, 32768),
)


class StreamType(enum.IntEnum):
    """``modal.stream_type.StreamType``: only ``PIPE`` is served."""

    PIPE = 1
    DEVNULL = 2
    STDOUT = 3


class Image(_m.Image):
    """A Modal image. ``debian_slim()`` is the default template; ``from_registry`` builds one."""

    def __init__(
        self, oci_ref: Optional[str] = None
    ) -> None:  # pylint: disable=super-init-not-called
        self._oci_ref = oci_ref

    @staticmethod
    def debian_slim(
        python_version: Optional[str] = None, force_build: bool = False
    ) -> "Image":
        _base.reject(
            "modal",
            "Image.debian_slim",
            "choosing a Python version",
            python_version=python_version,
        )
        return Image(None)

    @staticmethod
    def from_registry(
        tag: str,
        secret: Optional[Any] = None,
        *,
        setup_dockerfile_commands: List[
            str
        ] = [],  # pylint: disable=dangerous-default-value
        force_build: bool = False,
        add_python: Optional[str] = None,
        **kwargs: Any,
    ) -> "Image":
        _base.reject(
            "modal",
            "Image.from_registry",
            "registry credentials, setup commands, Python injection, or other image options (use a public OCI image)",
            secret=secret,
            setup_dockerfile_commands=setup_dockerfile_commands,
            add_python=add_python,
            **kwargs,
        )
        return Image(tag)

    def template_name(self) -> Optional[str]:
        """The DigitalOcean template this image is built into, or ``None`` for the default."""
        if self._oci_ref is None:
            return None
        return "modal-" + hashlib.sha256(self._oci_ref.encode()).hexdigest()[:16]


class Secret(_m.Secret):
    """A Modal secret held locally: ``from_dict`` and ``from_local_environ`` only."""

    def __init__(
        self, env: Mapping[str, Optional[str]]
    ) -> None:  # pylint: disable=super-init-not-called
        self._env = {k: v for k, v in env.items() if v is not None}

    @staticmethod
    def from_dict(
        env_dict: Dict[str, Optional[str]] = {},
    ) -> "Secret":  # pylint: disable=dangerous-default-value
        return Secret(env_dict)

    @staticmethod
    def from_local_environ(env_keys: List[str]) -> "Secret":
        missing = [k for k in env_keys if k not in os.environ]
        if missing:
            raise KeyError(
                "Missing local environment variables: %s" % ", ".join(missing)
            )
        return Secret({k: os.environ[k] for k in env_keys})


def size_for(cpu: Any, memory: Any, default: Optional[str]) -> Optional[str]:
    """The smallest sandbox size covering ``cpu`` (cores) and ``memory`` (MiB)."""
    if cpu is None and memory is None:
        return default
    want_cpu = cpu[0] if isinstance(cpu, (tuple, list)) else cpu
    want_mem = memory[0] if isinstance(memory, (tuple, list)) else memory
    for slug, vcpus, mem in SIZES:
        if vcpus >= (want_cpu or 0) and mem >= (want_mem or 0):
            return slug
    raise SandboxNotImplementedError(
        "Modal.Sandbox.create(cpu=%r, memory=%r)" % (cpu, memory),
        "a size that large (the largest is %s)" % SIZES[-1][0],
    )


def secrets_env(secrets: Optional[Any]) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for secret in secrets or []:
        if not isinstance(secret, Secret):
            raise SandboxNotImplementedError(
                "Modal.Sandbox(secrets=[<named Secret>])",
                "a secrets store (use Secret.from_dict)",
            )
        env.update(secret._env)  # pylint: disable=protected-access
    return env


def merged_env(
    env: Optional[Mapping[str, Optional[str]]], secrets: Optional[Any]
) -> Dict[str, str]:
    out = secrets_env(secrets)
    out.update({k: v for k, v in (env or {}).items() if v is not None})
    return out


def create_plan(a: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate Modal's ``Sandbox.create`` arguments; return what the Sandboxes API takes.

    Options that change what the sandbox is or how long it lives raise before any
    request. ``timeout=300`` is Modal's default, so it cannot be told apart from
    "not passed" and is accepted; any other lifetime raises.
    """
    q = "Sandbox.create"
    if a.get("timeout") not in (None, MODAL_DEFAULT_TIMEOUT):
        raise SandboxNotImplementedError(
            "Modal.%s(timeout=%r)" % (q, a["timeout"]), "a sandbox lifetime API"
        )
    _base.reject(
        "modal",
        q,
        "sandbox naming, tags, GPU, region, runtime, network policy, ports, volumes, PTY, probes, snapshots and lifetime options",
        name=a.get("name"),
        tags=a.get("tags"),
        idle_timeout=a.get("idle_timeout"),
        gpu=a.get("gpu"),
        cloud=a.get("cloud"),
        region=a.get("region"),
        runtime=a.get("runtime"),
        outbound_cidr_allowlist=a.get("outbound_cidr_allowlist"),
        outbound_domain_allowlist=a.get("outbound_domain_allowlist"),
        _experimental_outbound_policy=a.get("_experimental_outbound_policy"),
        inbound_cidr_allowlist=a.get("inbound_cidr_allowlist"),
        network_file_systems=a.get("network_file_systems"),
        volumes=a.get("volumes"),
        encrypted_ports=a.get("encrypted_ports"),
        h2_ports=a.get("h2_ports"),
        unencrypted_ports=a.get("unencrypted_ports"),
        custom_domain=a.get("custom_domain"),
        proxy=a.get("proxy"),
        readiness_probe=a.get("readiness_probe"),
        experimental_options=a.get("experimental_options"),
        pty_info=a.get("pty_info"),
        cidr_allowlist=a.get("cidr_allowlist"),
    )
    for flag in (
        "pty",
        "include_oidc_identity_token",
        "_experimental_enable_snapshot",
        "_experimental_persistent",
    ):
        if a.get(flag):
            raise SandboxNotImplementedError(
                "Modal.%s(%s=True)" % (q, flag),
                "a PTY, OIDC, snapshot or persistence option",
            )
    image = a.get("image")
    if image is not None and not isinstance(image, Image):
        raise SandboxNotImplementedError(
            "Modal.%s(image=<built image>)" % q, "image builds from instructions"
        )
    return {
        "image": image,
        "env_vars": merged_env(a.get("env"), a.get("secrets")) or None,
        "allow_internet_access": False if a.get("block_network") else None,
        "workdir": a.get("workdir"),
        "cpu": a.get("cpu"),
        "memory": a.get("memory"),
        "entrypoint": tuple(a.get("args") or ()),
    }


def process_options(
    q: str, a: Mapping[str, Any]
) -> Tuple[Optional[str], Dict[str, str], Optional[int]]:
    """``(workdir, env, timeout)`` from Modal's ``exec`` arguments; others raise."""
    if a.get("pty") or a.get("pty_info") or a.get("_pty_info"):
        raise SandboxNotImplementedError(
            "Modal.%s(pty=True)" % q, "a PTY (interactive terminal) API"
        )
    for stream in ("stdout", "stderr"):
        value = a.get(stream)
        if value not in (None, StreamType.PIPE, 1):
            raise SandboxNotImplementedError(
                "Modal.%s(%s=%r)" % (q, stream, value),
                "stream redirection (only StreamType.PIPE)",
            )
    return (
        a.get("workdir"),
        merged_env(a.get("env"), a.get("secrets")),
        a.get("timeout"),
    )
