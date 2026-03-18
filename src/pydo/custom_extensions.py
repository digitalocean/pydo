# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Multi-base-URL routing and SSE streaming support.

This file is preserved during ``make clean`` (matches the custom_*.py pattern)
and is NOT overwritten by code generation.

Architecture
------------
* ``_BaseURLProxy``  – lightweight proxy around a ``PipelineClient``
  that prepends a configured base URL to the generated path.  Reuses
  the original client's pipeline (auth, retry, logging).  Usable for
  any alternate host, not limited to inference endpoints.

* ``StreamingMixin`` / ``AsyncStreamingMixin``  – mix-in classes that provide
  the ``_auto_streaming_call`` method.  Can be mixed into any operation
  group (e.g. ``InferenceOperations``, ``AgentInferenceOperations``, or
  future groups) in their ``_patch.py`` files.

* ``SSEStream`` / ``AsyncSSEStream``  – iterators that parse Server-Sent
  Events from a streaming HTTP response and yield parsed JSON chunks.

* ``install_streaming_wrappers``  – called once in an Operations ``__init__``
  to automatically wrap every generated method that has a matching request
  builder.  When the user passes ``"stream": True`` in the body, the wrapper
  runs the pipeline in streaming mode and returns an SSEStream instead of
  falling through to the generated code (which would do ``response.json()``
  and fail on SSE data).

Extensibility
-------------
Both multi-base-URL **and** streaming are fully automatic for new endpoints:

1. Add the endpoint to the OpenAPI spec and run ``make generate``.
2. Autorest creates a new method in the generated operations class and a
   matching ``build_<tag>_<method>_request`` function.
3. ``install_streaming_wrappers`` discovers the pair at init time and creates
   a wrapper that intercepts ``stream: True``.
4. ``_BaseURLProxy`` routes the request to the correct server.

No manual changes to any ``_patch.py`` file are needed.
"""
import inspect
import json
import re
from io import IOBase
from typing import Any, AsyncIterator, Callable, Iterator, Optional
from urllib.parse import urlparse

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
    ResourceNotModifiedError,
    map_error,
)
from azure.core.rest import HttpRequest
from azure.core.utils import case_insensitive_dict


INFERENCE_BASE_URL = "https://inference.do-ai.run"

_STREAMING_ERROR_MAP = {
    401: ClientAuthenticationError,
    404: ResourceNotFoundError,
    409: ResourceExistsError,
    304: ResourceNotModifiedError,
}


# ---------------------------------------------------------------------------
# Multi-base-URL proxy
# ---------------------------------------------------------------------------


class _BaseURLProxy:
    """Proxy that redirects a PipelineClient to an alternate base URL.

    Reuses the wrapped client's pipeline (auth, retry, logging, etc.)
    while transparently prepending a different base URL to the
    generated path.  This is a generic utility and is not limited to
    inference endpoints.

    Parameters
    ----------
    original_client : PipelineClient
        The client whose pipeline (and transport) will be reused.
    base_url : str
        Target base URL (e.g. ``https://inference.do-ai.run``).
    """

    def __init__(self, original_client, base_url: str):
        self._original = original_client
        self._base_url = base_url.rstrip("/")

    def format_url(self, url_template: str, **kwargs: Any) -> str:
        parsed = urlparse(url_template)
        if not parsed.scheme:
            return self._base_url + url_template
        return url_template

    @property
    def _pipeline(self):
        return self._original._pipeline

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


# ---------------------------------------------------------------------------
# Auto-wrap generated methods with streaming detection
# ---------------------------------------------------------------------------


def _class_name_to_builder_prefix(class_name: str) -> str:
    """Convert ``'AgentInferenceOperations'`` → ``'agent_inference'``."""
    name = class_name.replace("Operations", "")
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def install_streaming_wrappers(
    instance,
    generated_class,
    ops_module,
    is_async: bool = False,
    builder_prefix: Optional[str] = None,
):
    """Scan *generated_class* for methods with a matching request builder in
    *ops_module* and install wrappers on *instance* that intercept
    ``body["stream"] == True``.

    *builder_prefix* defaults to the snake_case form of the class name (e.g.
    ``InferenceOperations`` → ``inference``).  Methods already overridden in
    ``type(instance)`` (the patched subclass) are skipped so explicit
    overrides take precedence.
    """
    if builder_prefix is None:
        builder_prefix = _class_name_to_builder_prefix(generated_class.__name__)

    for name in vars(generated_class):
        if name.startswith("_"):
            continue
        if name in type(instance).__dict__:
            continue
        builder_name = f"build_{builder_prefix}_{name}_request"
        builder = getattr(ops_module, builder_name, None)
        if builder is None:
            continue
        parent_fn = getattr(generated_class, name)
        if not callable(parent_fn):
            continue
        try:
            sig = inspect.signature(parent_fn)
            if "body" not in sig.parameters:
                continue
        except (ValueError, TypeError):
            continue

        _bind_streaming_wrapper(instance, name, parent_fn, builder, is_async)


def _bind_streaming_wrapper(instance, name, parent_fn, builder, is_async):
    """Create and install one streaming wrapper on *instance*."""
    this = instance

    if is_async:

        async def wrapper(*args, **kwargs):  # noqa: E303
            body = args[0] if args else kwargs.get("body")
            if isinstance(body, dict) and body.get("stream"):
                stream_kw = dict(kwargs)
                if args:
                    stream_kw["body"] = args[0]
                return await this._auto_streaming_call(builder, **stream_kw)
            return await parent_fn(this, *args, **kwargs)

    else:

        def wrapper(*args, **kwargs):  # noqa: E303
            body = args[0] if args else kwargs.get("body")
            if isinstance(body, dict) and body.get("stream"):
                stream_kw = dict(kwargs)
                if args:
                    stream_kw["body"] = args[0]
                return this._auto_streaming_call(builder, **stream_kw)
            return parent_fn(this, *args, **kwargs)

    wrapper.__name__ = name
    wrapper.__qualname__ = f"{type(instance).__name__}.{name}"
    wrapper.__doc__ = getattr(parent_fn, "__doc__", None)
    setattr(instance, name, wrapper)


# ---------------------------------------------------------------------------
# Streaming call mix-ins  (reused by any operation group's _patch.py)
# ---------------------------------------------------------------------------


class StreamingMixin:
    """Provides ``_auto_streaming_call`` for **sync** operation groups."""

    def _auto_streaming_call(
        self,
        builder: Callable[..., HttpRequest],
        **kwargs: Any,
    ) -> "SSEStream":
        body = kwargs.pop("body")

        error_map = dict(_STREAMING_ERROR_MAP)
        error_map.update(kwargs.pop("error_map", {}) or {})
        kwargs.pop("cls", None)

        _headers = case_insensitive_dict(kwargs.pop("headers", {}) or {})
        _params = kwargs.pop("params", {}) or {}
        content_type: Optional[str] = kwargs.pop(
            "content_type", _headers.pop("Content-Type", None)
        )
        content_type = content_type or "application/json"

        _json = None
        _content = None
        if isinstance(body, (IOBase, bytes)):
            _content = body
        else:
            body = {**body, "stream": True}
            _json = body

        _request = builder(
            content_type=content_type,
            json=_json,
            content=_content,
            headers=_headers,
            params=_params,
            **kwargs,
        )
        _request.url = self._client.format_url(_request.url)  # type: ignore[attr-defined]

        pipeline_response = self._client._pipeline.run(  # type: ignore[attr-defined]
            _request, stream=True
        )

        response = pipeline_response.http_response
        if response.status_code not in [200]:
            response.read()
            map_error(
                status_code=response.status_code,
                response=response,
                error_map=error_map,
            )
            raise HttpResponseError(response=response)

        return SSEStream(response)


class AsyncStreamingMixin:
    """Provides ``_auto_streaming_call`` for **async** operation groups."""

    async def _auto_streaming_call(
        self,
        builder: Callable[..., HttpRequest],
        **kwargs: Any,
    ) -> "AsyncSSEStream":
        body = kwargs.pop("body")

        error_map = dict(_STREAMING_ERROR_MAP)
        error_map.update(kwargs.pop("error_map", {}) or {})
        kwargs.pop("cls", None)

        _headers = case_insensitive_dict(kwargs.pop("headers", {}) or {})
        _params = kwargs.pop("params", {}) or {}
        content_type: Optional[str] = kwargs.pop(
            "content_type", _headers.pop("Content-Type", None)
        )
        content_type = content_type or "application/json"

        _json = None
        _content = None
        if isinstance(body, (IOBase, bytes)):
            _content = body
        else:
            body = {**body, "stream": True}
            _json = body

        _request = builder(
            content_type=content_type,
            json=_json,
            content=_content,
            headers=_headers,
            params=_params,
            **kwargs,
        )
        _request.url = self._client.format_url(_request.url)  # type: ignore[attr-defined]

        pipeline_response = await self._client._pipeline.run(  # type: ignore[attr-defined]
            _request, stream=True
        )

        response = pipeline_response.http_response
        if response.status_code not in [200]:
            await response.read()
            map_error(
                status_code=response.status_code,
                response=response,
                error_map=error_map,
            )
            raise HttpResponseError(response=response)

        return AsyncSSEStream(response)


# ---------------------------------------------------------------------------
# SSE stream iterators
# ---------------------------------------------------------------------------


class SSEStream:
    """Synchronous iterator over Server-Sent Events.

    Yields parsed JSON objects for each ``data:`` line.  Stops on
    ``data: [DONE]``.

    Usage::

        stream = client.<operations>.<method>(body={
            ...,
            "stream": True,
        })
        with stream:
            for chunk in stream:
                print(chunk)
    """

    def __init__(self, response: Any):
        self._response = response

    def __iter__(self) -> Iterator[dict]:
        return self._iter_events()

    def _iter_events(self) -> Iterator[dict]:
        buf = ""
        for raw in self._response.iter_bytes():
            text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            buf += text
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue

    def close(self) -> None:
        self._response.close()

    def __enter__(self) -> "SSEStream":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncSSEStream:
    """Asynchronous iterator over Server-Sent Events.

    Yields parsed JSON objects for each ``data:`` line.  Stops on
    ``data: [DONE]``.

    Usage::

        stream = await client.<operations>.<method>(body={
            ...,
            "stream": True,
        })
        async with stream:
            async for chunk in stream:
                print(chunk)
    """

    def __init__(self, response: Any):
        self._response = response

    def __aiter__(self) -> AsyncIterator[dict]:
        return self._iter_events()

    async def _iter_events(self) -> AsyncIterator[dict]:
        buf = ""
        async for raw in self._response.iter_bytes():
            text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            buf += text
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue

    def close(self) -> None:
        self._response.close()

    async def __aenter__(self) -> "AsyncSSEStream":
        return self

    async def __aexit__(self, *args: Any) -> None:
        self.close()
