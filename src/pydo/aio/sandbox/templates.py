# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Async custom sandbox templates: ``/v2/sandboxes/templates``.

Hand-written; preserved across ``make generate``. The async twin of
:mod:`pydo.sandbox.templates`: same names, with ``await`` and ``async for``.

.. code-block:: python

    template = await Template.create(name="my-template", source_oci_ref="r/i:v1")
    await template.wait_until_ready()
    sandbox = await Sandbox.create(template=template.name)
"""

import asyncio
import time
from typing import Any, AsyncIterator, Awaitable, Callable, List, Optional, Tuple

from pydo.sandbox import _templates as _t
from pydo.sandbox._connection import resolve
from pydo.sandbox._hybrid import by_id_or_self
from pydo.sandbox._templates import (
    ImageSource,
    TemplateBuildInfo,
    TemplateInfo,
    TemplateStatus,
)
from pydo.sandbox.errors import NotFoundError, SandboxError, SandboxTimeoutError

from ._transport import call as _call


def _make_client(token: Optional[str], api_url: Optional[str]) -> Any:
    from pydo.aio import Client  # pylint: disable=import-outside-toplevel

    resolved, url = resolve(token, api_url)
    return Client(resolved, endpoint=url)


class Pages:
    """One page at a time via :meth:`next_items`, or every item with ``async for``."""

    def __init__(
        self,
        fetch: Callable[[Optional[str]], Awaitable[Tuple[List[Any], Optional[str]]]],
        next_token: Optional[str] = None,
        close: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        self._fetch = fetch
        self._token = next_token or None
        self._started = False
        self._close = close

    @property
    def has_next(self) -> bool:
        """True until a page came back without a next-page token."""
        return not self._started or self._token is not None

    @property
    def next_token(self) -> Optional[str]:
        """The token that resumes after the last page read, if there is one."""
        return self._token

    async def next_items(self) -> List[Any]:
        """Reads the next page."""
        if not self.has_next:
            raise SandboxError("no more items to list")
        items, token = await self._fetch(self._token)
        self._started = True
        self._token = token or None
        return items

    async def close(self) -> None:
        """Closes the HTTP connection shared by the pages, if this list owns one."""
        if self._close:
            await self._close()

    async def __aiter__(self) -> AsyncIterator[Any]:
        while self.has_next:
            for item in await self.next_items():
                yield item


class Template:
    """A team custom template (async)."""

    def __init__(self, client: Any, info: TemplateInfo) -> None:
        self._client = client
        #: The record as last returned by the API. Await :meth:`refresh` to update it.
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
    async def create(
        cls,
        *,
        name: str,
        source_oci_ref: str,
        base_template: Optional[str] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Template":
        """Builds a custom template. Returns as soon as the build starts."""
        body = _t.create_body(name, source_oci_ref, base_template)
        client = _make_client(token, api_url)
        try:
            res = await _call(client.sandboxes.create_template, body) or {}
            return cls(client, _t.to_template(res.get("template")))
        except BaseException:
            await client.close()
            raise

    @classmethod
    async def get(
        cls,
        template_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Template":
        """Fetches a template by id."""
        client = _make_client(token, api_url)
        try:
            return cls(client, await _fetch(client, template_id))
        except BaseException:
            await client.close()
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
        """Lists your team's custom templates. ``async for`` over it, or await ``next_items()``."""
        client = _make_client(token, api_url)

        async def fetch(page_token: Optional[str]):
            res = (
                await _call(
                    client.sandboxes.list_templates,
                    page_size=limit,
                    page_token=page_token,
                )
                or {}
            )
            items = [cls(client, _t.to_template(r)) for r in res.get("templates") or []]
            return items, res.get("next_page_token")

        return Pages(fetch, next_token, close=client.close)

    async def refresh(self) -> TemplateInfo:
        """Reads the template again."""
        self.info = await _fetch(self._client, self.template_id)
        return self.info

    async def update(
        self,
        *,
        source_oci_ref: Optional[str] = None,
        base_template: Optional[str] = None,
    ) -> TemplateInfo:
        """Changes the image and/or base template and starts a new build."""
        body = _t.update_body(source_oci_ref, base_template)
        res = (
            await _call(self._client.sandboxes.update_template, self.template_id, body)
            or {}
        )
        self.info = _t.to_template(res.get("template"))
        return self.info

    @by_id_or_self
    async def delete(self) -> bool:
        """Deletes the template. Also callable as ``await Template.delete(template_id)``."""
        return await _delete(self._client, self.template_id)

    @delete.by_id
    async def delete(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        template_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> bool:
        async with _make_client(token, api_url) as client:
            return await _delete(client, _t.require_template_id(template_id))

    def builds(self, *, limit: Optional[int] = None) -> Pages:
        """Lists the template's builds."""

        async def fetch(page_token: Optional[str]):
            res = (
                await _call(
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

    async def build(self, build_id: str) -> TemplateBuildInfo:
        """Fetches one build of the template."""
        if not build_id or not str(build_id).strip():
            raise SandboxError("`build_id` is required")
        res = (
            await _call(
                self._client.sandboxes.get_template_build, self.template_id, build_id
            )
            or {}
        )
        return _t.to_build(res.get("build"))

    async def wait_until_ready(
        self, *, timeout: float = 600.0, poll_interval: float = 2.0
    ) -> "Template":
        """Polls until the template is ready. Raises if the build failed or the wait runs out."""
        deadline = time.monotonic() + timeout
        while True:
            if self.status == _t.READY:
                return self
            if self.status == _t.FAILED:
                raise SandboxError(await self._failure())
            if time.monotonic() >= deadline:
                raise SandboxTimeoutError(
                    "template %s was not ready in time (last status %s)"
                    % (self.template_id, self.status)
                )
            await asyncio.sleep(poll_interval)
            await self.refresh()

    async def close(self) -> None:
        """Closes the HTTP connection. Does not delete the template."""
        await self._client.close()

    async def __aenter__(self) -> "Template":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    async def _failure(self) -> str:
        try:
            page = await self.builds().next_items()
        except SandboxError:
            page = []
        return _t.failure_message(self.template_id, page)


async def _fetch(client: Any, template_id: str) -> TemplateInfo:
    res = (
        await _call(client.sandboxes.get_template, _t.require_template_id(template_id))
        or {}
    )
    return _t.to_template(res.get("template"))


async def _delete(client: Any, template_id: str) -> bool:
    try:
        await _call(client.sandboxes.delete_template, template_id)
        return True
    except NotFoundError:
        return False


__all__ = ["ImageSource", "Pages", "Template", "TemplateBuildInfo", "TemplateInfo"]
