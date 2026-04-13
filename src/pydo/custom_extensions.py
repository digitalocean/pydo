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
import asyncio
import codecs
import inspect
import json
import random
import re
import time
from io import IOBase
from typing import (
    Any,
    AsyncIterator,
    AsyncGenerator,
    Callable,
    Dict,
    Iterator,
    Optional,
)
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

try:
    from azure.core.exceptions import ServiceRequestError
except ImportError:  # pragma: no cover
    ServiceRequestError = RuntimeError  # type: ignore[misc,assignment]

from pydo.exceptions import (
    SSEStreamDecodeError,
    SSEStreamRetryExhaustedError,
    SSEStreamTransportError,
)


INFERENCE_BASE_URL = "https://inference.do-ai.run"


def recover_async_invoke_from_200_error(exc: HttpResponseError):
    """If ``create_async_invoke`` failed only because the status was 200, not 202.

    The published spec lists **202 Accepted** for async-invoke; some deployments
    return **200 OK** with the same JSON (e.g. ``status: "QUEUED"``). The
    generated client only accepts 202 and raises :class:`HttpResponseError`.
    When the body looks like a valid async-invocation record, return it as a
    normal success payload.
    """
    if getattr(exc, "status_code", None) != 200:
        return None
    resp = exc.response
    if resp is None:
        return None
    try:
        data = resp.json()
    except (TypeError, ValueError, AttributeError):
        return None
    if not isinstance(data, dict):
        return None
    if "request_id" not in data or "status" not in data:
        return None
    return data


# ---------------------------------------------------------------------------
# DotDict — recursive attribute-style access over plain JSON dicts
# ---------------------------------------------------------------------------


class DotDict(dict):
    """A ``dict`` subclass that supports attribute-style access.

    Recursively wraps nested dicts and lists so that the entire response
    tree is accessible with dot notation::

        completion = client.chat.completions.create(...)
        print(completion.choices[0].message.content)  # works!
        print(completion["choices"][0]["message"]["content"])  # also works

    ``DotDict`` is a real ``dict``, so ``json.dumps``, ``in``, ``.get()``,
    ``.items()`` etc. all behave as expected.
    """

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(
                f"{type(self).__name__!r} object has no attribute {name!r}"
            ) from None

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "__class__":
            super().__setattr__(name, value)
        else:
            self[name] = value

    def __delattr__(self, name: str) -> None:
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name) from None

    def __repr__(self) -> str:
        return f"DotDict({dict.__repr__(self)})"


def _wrap(obj: Any) -> Any:
    """Recursively wrap dicts → DotDict and lists → list-of-wrapped.

    If the dict has an ``object`` key that matches a known response type
    (e.g. ``"chat.completion"``), the top-level wrapper is a typed subclass
    from :mod:`pydo.types` instead of plain :class:`DotDict`.
    """
    if isinstance(obj, DotDict):
        return obj
    if isinstance(obj, dict):
        wrapped = DotDict({k: _wrap(v) for k, v in obj.items()})
        obj_field = wrapped.get("object")
        if obj_field:
            _ensure_type_map()
            cls = _OBJECT_TYPE_MAP.get(obj_field)
            if cls is not None:
                wrapped.__class__ = cls
        return wrapped
    if isinstance(obj, list):
        return [_wrap(item) for item in obj]
    return obj


# Lazy-loaded type registry — populated on first access.
_OBJECT_TYPE_MAP: dict = {}
_OBJECT_TYPE_MAP_LOADED = False


def _ensure_type_map() -> None:
    global _OBJECT_TYPE_MAP, _OBJECT_TYPE_MAP_LOADED  # noqa: PLW0603
    if _OBJECT_TYPE_MAP_LOADED:
        return
    _OBJECT_TYPE_MAP_LOADED = True
    try:
        from pydo.types._type_registry import _OBJECT_TYPE_MAP as _m  # type: ignore

        _OBJECT_TYPE_MAP.update(_m)
    except ImportError:
        pass


_STREAMING_ERROR_MAP = {
    401: ClientAuthenticationError,
    404: ResourceNotFoundError,
    409: ResourceExistsError,
    304: ResourceNotModifiedError,
}

# Transient failures while reading a streamed response body.
_STREAM_READ_ERRORS = (
    ServiceRequestError,
    TimeoutError,
    BrokenPipeError,
    ConnectionError,
    ConnectionResetError,
)


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

    On read failures, raises :exc:`~pydo.exceptions.SSEStreamTransportError`.
    On invalid JSON for a full line, raises
    :exc:`~pydo.exceptions.SSEStreamDecodeError`.

    Usage::

        stream = client.<operations>.<method>(body={
            ...,
            "stream": True,
        })
        with stream:
            for chunk in stream:
                print(chunk)

    For automatic retries on **transient** transport errors **before any chunk
    is yielded**, see :func:`iter_sse_with_retry`.
    """

    def __init__(self, response: Any):
        self._response = response

    def __iter__(self) -> Iterator[dict]:
        return self._iter_events()

    def _iter_events(self) -> Iterator[dict]:
        buf = ""
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        try:
            for raw in self._response.iter_bytes():
                text = decoder.decode(raw, False) if isinstance(raw, bytes) else raw
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
                            yield _wrap(json.loads(data))
                        except json.JSONDecodeError as err:
                            snippet = data if len(data) <= 240 else data[:240] + "..."
                            raise SSEStreamDecodeError(
                                f"invalid JSON in SSE data line: {snippet!r}"
                            ) from err
            if buf.strip():
                raise SSEStreamTransportError(
                    "SSE stream ended with an incomplete line (connection closed "
                    "early or truncated transfer)."
                )
        except SSEStreamTransportError:
            raise
        except SSEStreamDecodeError:
            raise
        except _STREAM_READ_ERRORS as err:
            raise SSEStreamTransportError(
                "SSE stream interrupted while reading bytes (network drop, "
                "timeout, or connection reset)."
            ) from err

    def close(self) -> None:
        self._response.close()

    def __enter__(self) -> "SSEStream":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncSSEStream:
    """Asynchronous iterator over Server-Sent Events.

    Transport and decode errors match :class:`SSEStream`.  See
    :func:`async_iter_sse_with_retry` for retries before the first chunk.
    """

    def __init__(self, response: Any):
        self._response = response

    def __aiter__(self) -> AsyncIterator[dict]:
        return self._iter_events()

    async def _iter_events(self) -> AsyncIterator[dict]:
        buf = ""
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        try:
            async for raw in self._response.iter_bytes():
                text = decoder.decode(raw, False) if isinstance(raw, bytes) else raw
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
                            yield _wrap(json.loads(data))
                        except json.JSONDecodeError as err:
                            snippet = data if len(data) <= 240 else data[:240] + "..."
                            raise SSEStreamDecodeError(
                                f"invalid JSON in SSE data line: {snippet!r}"
                            ) from err
            if buf.strip():
                raise SSEStreamTransportError(
                    "SSE stream ended with an incomplete line (connection closed "
                    "early or truncated transfer)."
                )
        except SSEStreamTransportError:
            raise
        except SSEStreamDecodeError:
            raise
        except _STREAM_READ_ERRORS as err:
            raise SSEStreamTransportError(
                "SSE stream interrupted while reading bytes (network drop, "
                "timeout, or connection reset)."
            ) from err

    async def close(self) -> None:
        result = self._response.close()
        if inspect.isawaitable(result):
            await result

    async def __aenter__(self) -> "AsyncSSEStream":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


def iter_sse_with_retry(
    stream_factory: Callable[[], "SSEStream"],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_jitter: float = 0.15,
) -> Iterator[Dict[str, Any]]:
    """Yield SSE JSON chunks, retrying **only** on :exc:`SSEStreamTransportError`
    **before** any chunk is yielded.

    After the first chunk, transport errors are re-raised immediately (retrying
    would duplicate content).  Uses exponential backoff with optional jitter.

    *stream_factory* must return a **new** :class:`SSEStream` on each call (new
    HTTP request), e.g. ``lambda: client.inference.create_chat_completion({...})``.

    Raises :exc:`~pydo.exceptions.SSEStreamRetryExhaustedError` if all attempts fail.
    """
    last_exc: Optional[BaseException] = None
    for attempt in range(max_attempts):
        stream = stream_factory()
        yielded = False
        try:
            with stream:
                for chunk in stream:
                    yielded = True
                    yield chunk
            return
        except SSEStreamTransportError as exc:
            last_exc = exc
            if yielded:
                raise
            if attempt == max_attempts - 1:
                raise SSEStreamRetryExhaustedError(
                    f"SSE stream failed after {max_attempts} attempt(s)"
                ) from exc
            delay = base_delay * (2**attempt) + random.uniform(0.0, max_jitter)
            time.sleep(delay)
        except SSEStreamDecodeError:
            raise

    raise SSEStreamRetryExhaustedError("SSE stream failed") from last_exc


async def async_iter_sse_with_retry(
    stream_factory: Callable[[], "AsyncSSEStream"],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_jitter: float = 0.15,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Async variant of :func:`iter_sse_with_retry`."""
    last_exc: Optional[BaseException] = None
    for attempt in range(max_attempts):
        stream = stream_factory()
        yielded = False
        try:
            async with stream:
                async for chunk in stream:
                    yielded = True
                    yield chunk
            return
        except SSEStreamTransportError as exc:
            last_exc = exc
            if yielded:
                raise
            if attempt == max_attempts - 1:
                raise SSEStreamRetryExhaustedError(
                    f"SSE stream failed after {max_attempts} attempt(s)"
                ) from exc
            delay = base_delay * (2**attempt) + random.uniform(0.0, max_jitter)
            await asyncio.sleep(delay)
        except SSEStreamDecodeError:
            raise

    raise SSEStreamRetryExhaustedError("SSE stream failed") from last_exc
