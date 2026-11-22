# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Custom sandbox templates: ``/v2/sandboxes/templates``.

Hand-written; preserved across ``make generate``. A template is built by
rebasing a customer OCI image onto a base template. The build is asynchronous:
create, wait until it is ready, then pass the template's name to
``Sandbox.create``.

.. code-block:: python

    template = Template.create(
        name="my-template",
        source_oci_ref="registry.digitalocean.com/my-team/my-image:v1",
    )
    template.wait_until_ready()
    sandbox = Sandbox.create(template=template.name)
"""

import time
from typing import Any, Callable, Iterator, List, Optional, Tuple, TypeVar

from . import _templates as _t
from ._connection import resolve
from ._hybrid import by_id_or_self
from ._templates import (
    ImageSource,
    TemplateBuildInfo,
    TemplateInfo,
    TemplateStatus,
)
from ._transport import call as _call
from .errors import NotFoundError, SandboxError, SandboxTimeoutError

T = TypeVar("T")


def _make_client(token: Optional[str], api_url: Optional[str]) -> Any:
    from pydo import Client  # pylint: disable=import-outside-toplevel

    resolved, url = resolve(token, api_url)
    return Client(resolved, endpoint=url)


class Pages:
    """One page at a time via :meth:`next_items`, or every item by iterating."""

    def __init__(
        self,
        fetch: Callable[[Optional[str]], Tuple[List[Any], Optional[str]]],
        next_token: Optional[str] = None,
    ) -> None:
        self._fetch = fetch
        self._token = next_token or None
        self._started = False

    @property
    def has_next(self) -> bool:
        """True until a page came back without a next-page token."""
        return not self._started or self._token is not None

    @property
    def next_token(self) -> Optional[str]:
        """The token that resumes after the last page read, if there is one."""
        return self._token

    def next_items(self) -> List[Any]:
        """Reads the next page."""
        if not self.has_next:
            raise SandboxError("no more items to list")
        items, token = self._fetch(self._token)
        self._started = True
        self._token = token or None
        return items

    def __iter__(self) -> Iterator[Any]:
        while self.has_next:
            yield from self.next_items()


class Template:
    """A team custom template."""

    def __init__(self, client: Any, info: TemplateInfo) -> None:
        self._client = client
        #: The record as last returned by the API. Call :meth:`refresh` to update it.
        self.info = info

    def __repr__(self) -> str:
        return "Template(template_id=%r, name=%r, status=%r)" % (
            self.template_id,
            self.name,
            self.status,
        )

    @property
    def template_id(self) -> str:
        return self.info.template_id

    @property
    def name(self) -> str:
        """The name ``Sandbox.create(template=...)`` takes."""
        return self.info.name

    @property
    def status(self) -> TemplateStatus:
        return self.info.status

    @classmethod
    def create(
        cls,
        *,
        name: str,
        source_oci_ref: str,
        base_template: Optional[str] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Template":
        """Builds a custom template. Returns as soon as the build starts.

        Call :meth:`wait_until_ready` before using it.

        :keyword name: Template name. It must not collide with a global base template name.
        :keyword source_oci_ref: The OCI image, ``registry/repository:tag`` or ``@digest``.
        :keyword base_template: The base template to rebase onto. Defaults to ``coding-base``.
        """
        body = _t.create_body(name, source_oci_ref, base_template)
        client = _make_client(token, api_url)
        try:
            res = _call(client.sandboxes.create_template, body) or {}
            return cls(client, _t.to_template(res.get("template")))
        except BaseException:
            client.close()
            raise

    @classmethod
    def get(
        cls,
        template_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Template":
        """Fetches a template by id."""
        client = _make_client(token, api_url)
        try:
            return cls(client, _fetch(client, template_id))
        except BaseException:
            client.close()
            raise

    @classmethod
    def list(
        cls,
        *,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> Pages:
        """Lists your team's custom templates. Global base templates are not included."""
        client = _make_client(token, api_url)

        def fetch(page_token: Optional[str]):
            res = (
                _call(
                    client.sandboxes.list_templates,
                    page_size=limit,
                    page_token=page_token,
                )
                or {}
            )
            items = [cls(client, _t.to_template(r)) for r in res.get("templates") or []]
            return items, res.get("next_page_token")

        return Pages(fetch, next_token)

    def refresh(self) -> TemplateInfo:
        """Reads the template again."""
        self.info = _fetch(self._client, self.template_id)
        return self.info

    def update(
        self,
        *,
        source_oci_ref: Optional[str] = None,
        base_template: Optional[str] = None,
    ) -> TemplateInfo:
        """Changes the image and/or base template and starts a new build.

        Call :meth:`wait_until_ready` afterwards.
        """
        body = _t.update_body(source_oci_ref, base_template)
        res = (
            _call(self._client.sandboxes.update_template, self.template_id, body) or {}
        )
        self.info = _t.to_template(res.get("template"))
        return self.info

    @by_id_or_self
    def delete(self) -> bool:
        """Deletes the template. Returns ``False`` when it is already gone.

        Also callable as ``Template.delete(template_id)``.
        """
        return _delete(self._client, self.template_id)

    @delete.by_id
    def delete(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        template_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> bool:
        with _make_client(token, api_url) as client:
            return _delete(client, _t.require_template_id(template_id))

    def builds(self, *, limit: Optional[int] = None) -> Pages:
        """Lists the template's builds."""

        def fetch(page_token: Optional[str]):
            res = (
                _call(
                    self._client.sandboxes.list_template_builds,
                    self.template_id,
                    page_size=limit,
                    page_token=page_token,
                )
                or {}
            )
            return [_t.to_build(b) for b in res.get("builds") or []], res.get(
                "next_page_token"
            )

        return Pages(fetch)

    def build(self, build_id: str) -> TemplateBuildInfo:
        """Fetches one build of the template."""
        if not build_id or not str(build_id).strip():
            raise SandboxError("`build_id` is required")
        res = (
            _call(self._client.sandboxes.get_template_build, self.template_id, build_id)
            or {}
        )
        return _t.to_build(res.get("build"))

    def wait_until_ready(
        self, *, timeout: float = 600.0, poll_interval: float = 2.0
    ) -> "Template":
        """Polls until the template is ready.

        Raises if the build failed (with the newest failed build's error, when
        the API gives one) or the wait runs out.
        """
        deadline = time.monotonic() + timeout
        while True:
            if self.status == _t.READY:
                return self
            if self.status == _t.FAILED:
                raise SandboxError(self._failure())
            if time.monotonic() >= deadline:
                raise SandboxTimeoutError(
                    "template %s was not ready in time (last status %s)"
                    % (self.template_id, self.status)
                )
            time.sleep(poll_interval)
            self.refresh()

    def close(self) -> None:
        """Closes the HTTP connection. Does not delete the template."""
        self._client.close()

    def __enter__(self) -> "Template":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def _failure(self) -> str:
        try:
            page = self.builds().next_items()
        except SandboxError:
            page = []
        return _t.failure_message(self.template_id, page)


def _fetch(client: Any, template_id: str) -> TemplateInfo:
    res = (
        _call(client.sandboxes.get_template, _t.require_template_id(template_id)) or {}
    )
    return _t.to_template(res.get("template"))


def _delete(client: Any, template_id: str) -> bool:
    try:
        _call(client.sandboxes.delete_template, template_id)
        return True
    except NotFoundError:
        return False


__all__ = ["ImageSource", "Pages", "Template", "TemplateBuildInfo", "TemplateInfo"]
