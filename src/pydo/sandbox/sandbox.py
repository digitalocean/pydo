# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""DigitalOcean Sandbox SDK over ``/v2/sandboxes``.

Hand-written; preserved across ``make generate``. Every call goes through the
generated ``client.sandboxes`` operations, so auth, retries and User-Agent
match the rest of pydo.

.. code-block:: python

    from pydo.sandbox import Sandbox

    sandbox = Sandbox.create(template="coding-base")
    sandbox.pause()
    sandbox.resume()
    sandbox.kill()
"""

import time
from typing import Any, Iterator, List, Mapping, Optional

from . import types as _t
from ._connection import resolve
from ._hybrid import by_id_or_self
from ._transport import call as _call
from .commands import Commands
from .errors import NotFoundError, SandboxError, SandboxTimeoutError
from .types import SandboxInfo, SandboxState, create_body, require_id, to_info


def _make_client(token: Optional[str], api_url: Optional[str]) -> Any:
    from pydo import Client  # pylint: disable=import-outside-toplevel

    resolved, url = resolve(token, api_url)
    return Client(resolved, endpoint=url)


class Sandbox:
    """A DigitalOcean Sandbox.

    Create one with :meth:`create`, or find one with :meth:`get`,
    :meth:`connect` or :meth:`list`. Use it as a context manager to delete it
    at the end of the block.
    """

    def __init__(self, client: Any, info: SandboxInfo) -> None:
        self._client = client
        #: The record as last returned by the API. Call :meth:`get_info` to refresh it.
        self.info = info
        #: Start, list and stream the commands running in this sandbox.
        self.commands = Commands(client, info.sandbox_id)

    def __repr__(self) -> str:
        return "Sandbox(sandbox_id=%r, state=%r)" % (self.sandbox_id, self.state)

    @property
    def sandbox_id(self) -> str:
        return self.info.sandbox_id

    @property
    def state(self) -> SandboxState:
        return self.info.state

    @property
    def template(self) -> str:
        return self.info.template

    # -- constructors --------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        template: Optional[str] = None,
        size: Optional[str] = None,
        allow_internet_access: Optional[bool] = None,
        env_vars: Optional[Mapping[str, str]] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Sandbox":
        """Creates a sandbox. Returns once it is running.

        :keyword template: The template to create the sandbox from. Defaults to ``coding-base``.
        :keyword size: A size slug. Defaults to ``mars-2vcpu-4gb``.
        :keyword allow_internet_access: ``False`` limits egress to the platform
            file-transfer host. Defaults to unrestricted.
        :keyword env_vars: Environment variables for the sandbox. The values are secrets.
        :keyword token: An API token. Defaults to ``DIGITALOCEAN_ACCESS_TOKEN``.
        :keyword api_url: The API origin. Defaults to ``DIGITALOCEAN_API_URL``,
            then https://api.digitalocean.com.
        """
        body = create_body(template, size, allow_internet_access, env_vars)
        client = _make_client(token, api_url)
        try:
            return cls(client, to_info(_call(client.sandboxes.create, body)))
        except BaseException:
            client.close()
            raise

    @classmethod
    def get(
        cls,
        sandbox_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Sandbox":
        """Fetches a sandbox by id."""
        client = _make_client(token, api_url)
        try:
            return cls(
                client, to_info(_call(client.sandboxes.get, require_id(sandbox_id)))
            )
        except BaseException:
            client.close()
            raise

    @classmethod
    def connect(
        cls,
        sandbox_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "Sandbox":
        """Fetches a sandbox by id and resumes it if it is paused."""
        sandbox = cls.get(sandbox_id, token=token, api_url=api_url)
        if sandbox.state == _t.PAUSED:
            sandbox.resume()
        return sandbox

    @classmethod
    def list(
        cls,
        *,
        state: Optional[SandboxState] = None,
        limit: Optional[int] = None,
        next_token: Optional[str] = None,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> "SandboxPaginator":
        """Lists the team's sandboxes.

        Iterate the result to walk every page, or call
        :meth:`SandboxPaginator.next_items` for one page at a time.
        """
        return SandboxPaginator(
            _make_client(token, api_url),
            state=state,
            limit=limit,
            next_token=next_token,
        )

    # -- instance operations ------------------------------------------

    def get_info(self) -> SandboxInfo:
        """Reads the sandbox again."""
        self.info = to_info(_call(self._client.sandboxes.get, self.sandbox_id))
        return self.info

    def is_running(self) -> bool:
        """True when the sandbox is running right now. Reads the API."""
        return self.get_info().state == _t.RUNNING

    def resume(self) -> SandboxInfo:
        """Resumes a paused sandbox."""
        self.info = to_info(_call(self._client.sandboxes.post_resume, self.sandbox_id))
        return self.info

    @by_id_or_self
    def pause(self) -> SandboxInfo:
        """Pauses the sandbox. Resume it to use it again.

        Also callable as ``Sandbox.pause(sandbox_id)``.
        """
        self.info = to_info(_call(self._client.sandboxes.post_pause, self.sandbox_id))
        return self.info

    @pause.by_id
    def pause(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        sandbox_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> SandboxInfo:
        with _make_client(token, api_url) as client:
            return to_info(_call(client.sandboxes.post_pause, require_id(sandbox_id)))

    @by_id_or_self
    def kill(self) -> bool:
        """Deletes the sandbox. Returns ``False`` when it is already gone.

        Also callable as ``Sandbox.kill(sandbox_id)``.
        """
        return _delete(self._client, self.sandbox_id)

    @kill.by_id
    def kill(  # type: ignore[no-redef]  # pylint: disable=function-redefined
        cls,
        sandbox_id: str,
        *,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> bool:
        with _make_client(token, api_url) as client:
            return _delete(client, require_id(sandbox_id))

    def wait_until_running(
        self, *, timeout: float = 120.0, poll_interval: float = 1.0
    ) -> "Sandbox":
        """Polls until the sandbox is running. Raises if it is paused or the wait runs out."""
        deadline = time.monotonic() + timeout
        while True:
            if self.state == _t.RUNNING:
                return self
            if self.state != _t.CREATING:
                raise SandboxError(
                    "sandbox %s will not become running: %s"
                    % (self.sandbox_id, self.state)
                )
            if time.monotonic() >= deadline:
                raise SandboxTimeoutError(
                    "sandbox %s was not running in time (last state %s)"
                    % (self.sandbox_id, self.state)
                )
            time.sleep(poll_interval)
            self.get_info()

    def close(self) -> None:
        """Closes the HTTP connection. Does not delete the sandbox."""
        self._client.close()

    def __enter__(self) -> "Sandbox":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        """Deletes the sandbox and closes the connection."""
        try:
            self.kill()
        finally:
            self.close()


class SandboxPaginator:
    """One page at a time via :meth:`next_items`, or every sandbox by iterating."""

    def __init__(
        self,
        client: Any,
        *,
        state: Optional[SandboxState],
        limit: Optional[int],
        next_token: Optional[str],
    ) -> None:
        self._client = client
        self._state = state
        self._limit = limit
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

    def next_items(self) -> List[Sandbox]:
        """Reads the next page."""
        if not self.has_next:
            raise SandboxError("no more sandboxes to list")
        res = _call(
            self._client.sandboxes.list,
            page_size=self._limit,
            page_token=self._token,
            state=self._state,
        )
        self._started = True
        self._token = (res or {}).get("next_page_token") or None
        return [
            Sandbox(self._client, to_info({"sandbox": item}))
            for item in (res or {}).get("sandboxes") or []
        ]

    def __iter__(self) -> Iterator[Sandbox]:
        while self.has_next:
            yield from self.next_items()


def _delete(client: Any, sandbox_id: str) -> bool:
    try:
        _call(client.sandboxes.delete, sandbox_id)
        return True
    except NotFoundError:
        return False
