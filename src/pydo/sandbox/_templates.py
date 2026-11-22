# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Types and helpers shared by the sync and async sandbox templates.

Hand-written; preserved across ``make generate``.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .errors import SandboxError
from .types import _parse_time

#: Template status values: ``TEMPLATE_STATUS_PENDING``, ``..._BUILDING``,
#: ``..._READY``, ``..._FAILED`` (and ``..._UNSPECIFIED``).
TemplateStatus = str
READY = "TEMPLATE_STATUS_READY"
FAILED = "TEMPLATE_STATUS_FAILED"
BUILD_FAILED = "TEMPLATE_BUILD_STATUS_FAILED"

#: Base template used when ``base_template`` is omitted.
DEFAULT_BASE_TEMPLATE = "coding-base"


@dataclass
class ImageSource:
    """A customer OCI image."""

    registry: Optional[str] = None
    repository: Optional[str] = None
    tag: Optional[str] = None
    digest: Optional[str] = None


@dataclass
class TemplateInfo:
    """A template record as the API last returned it."""

    template_id: str
    name: str
    status: TemplateStatus
    #: The base template the image was rebased onto.
    base_template: Optional[str] = None
    image: Optional[ImageSource] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class TemplateBuildInfo:
    """One build of a template."""

    build_id: str
    template_id: str
    status: str
    name: Optional[str] = None
    #: Set when the build failed.
    error: Optional[str] = None
    base_template: Optional[str] = None
    image: Optional[ImageSource] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


def _image(raw: Any) -> Optional[ImageSource]:
    if not isinstance(raw, dict):
        return None
    return ImageSource(
        registry=raw.get("registry"),
        repository=raw.get("repository"),
        tag=raw.get("tag"),
        digest=raw.get("digest"),
    )


def _time(raw: Any) -> Optional[datetime]:
    return _parse_time(raw) if raw else None


def to_template(raw: Any) -> TemplateInfo:
    """Builds a :class:`TemplateInfo` from a template object."""
    if not isinstance(raw, dict) or not raw.get("template_id"):
        raise SandboxError("the API response did not include the template")
    spec = raw.get("spec") or {}
    return TemplateInfo(
        template_id=raw["template_id"],
        name=raw.get("name") or "",
        status=raw.get("status") or "TEMPLATE_STATUS_UNSPECIFIED",
        base_template=spec.get("base_template"),
        image=_image(spec.get("image")),
        created_at=_time(raw.get("created_at")),
        updated_at=_time(raw.get("updated_at")),
    )


def to_build(raw: Any) -> TemplateBuildInfo:
    """Builds a :class:`TemplateBuildInfo` from a build object."""
    if not isinstance(raw, dict) or not raw.get("build_id"):
        raise SandboxError("the API response did not include the build")
    spec = raw.get("spec") or {}
    return TemplateBuildInfo(
        build_id=raw["build_id"],
        template_id=raw.get("template_id") or "",
        status=raw.get("status") or "TEMPLATE_BUILD_STATUS_UNSPECIFIED",
        name=raw.get("name"),
        error=raw.get("error") or None,
        base_template=spec.get("base_template"),
        image=_image(spec.get("image")),
        created_at=_time(raw.get("created_at")),
        updated_at=_time(raw.get("updated_at")),
    )


def create_body(
    name: str, source_oci_ref: str, base_template: Optional[str]
) -> Dict[str, Any]:
    """Validates create arguments and builds the request body."""
    if not name or not str(name).strip():
        raise SandboxError("Template.create: `name` is required")
    if not source_oci_ref or not str(source_oci_ref).strip():
        raise SandboxError("Template.create: `source_oci_ref` is required")
    return {
        "name": name,
        "base_template": base_template or DEFAULT_BASE_TEMPLATE,
        "source_oci_ref": source_oci_ref,
    }


def update_body(
    source_oci_ref: Optional[str], base_template: Optional[str]
) -> Dict[str, Any]:
    """Validates update arguments and builds the request body."""
    body: Dict[str, Any] = {}
    if source_oci_ref and source_oci_ref.strip():
        body["source_oci_ref"] = source_oci_ref
    if base_template and base_template.strip():
        body["base_template"] = base_template
    if not body:
        raise SandboxError(
            "template.update: pass `source_oci_ref` and/or `base_template`"
        )
    return body


def require_template_id(template_id: str) -> str:
    if not template_id or not str(template_id).strip():
        raise SandboxError("`template_id` is required")
    return template_id


def failure_message(template_id: str, builds: List[TemplateBuildInfo]) -> str:
    """Explains a failed template with the newest failed build's error."""
    message = "template %s failed to build" % template_id
    failed = [b for b in builds if b.status == BUILD_FAILED and b.error]
    failed.sort(
        key=lambda b: b.updated_at.timestamp() if b.updated_at else 0, reverse=True
    )
    return "%s: %s" % (message, failed[0].error) if failed else message
