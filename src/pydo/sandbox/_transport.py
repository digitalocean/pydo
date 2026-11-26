# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""How the sync sandbox SDK calls the generated operations.

Hand-written; preserved across ``make generate``.
"""

import json
from typing import Any, Mapping, Optional

from azure.core.exceptions import HttpResponseError
from azure.core.rest import HttpRequest

from .errors import build_error, to_sandbox_error, unwrap, with_response


def guard_response(pipeline_response: Any) -> None:
    """``raw_response_hook``: every sandbox endpoint answers JSON.

    Any other content type means something else replied (a gateway's HTML 404 or
    502 page, a route that is not deployed). The generated operation would fail
    on it with a bare JSON decode error that hides the status, so raise the usual
    typed error with the status and the start of the body instead.
    """
    guard_http_response(pipeline_response.http_response)


def guard_http_response(response: Any) -> None:
    """:func:`guard_response` for a response already in hand."""
    ctype = (response.headers.get("Content-Type") or "").lower()
    if response.status_code == 204 or not ctype or "json" in ctype:
        return
    try:
        body = " ".join(response.text().split())[:200]
    except Exception:  # pylint: disable=broad-except
        body = ""
    message = "unexpected %s response (HTTP %d)" % (
        ctype.split(";")[0],
        response.status_code,
    )
    raise build_error(
        response.status_code, None, message + (": " + body if body else "")
    )


def call(operation: Any, *args: Any, **kwargs: Any) -> Any:
    """Runs a generated operation and raises a typed error for any failure."""
    try:
        return unwrap(
            operation(
                *args,
                cls=with_response,
                raw_response_hook=guard_response,
                **kwargs,
            )
        )
    except HttpResponseError as err:
        raise to_sandbox_error(err) from err


def parse_response(response: Any) -> Any:
    """Returns the JSON body of a raw response, or raises the typed error.

    For endpoints without a generated operation, sent with
    ``client.send_request``. That method does no error handling, so this does
    what :func:`call` does for a generated operation.
    """
    guard_http_response(response)
    try:
        body = response.json() if response.content else None
    except ValueError:
        body = None
    if response.status_code >= 400:
        raise build_error(response.status_code, body, None, response.headers)
    return body


def raw_request(
    method: str,
    path: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    body: Any = None,
) -> HttpRequest:
    """Builds a request for ``path`` (relative to the API origin) with a JSON body."""
    return HttpRequest(
        method,
        path,
        params={k: v for k, v in (params or {}).items() if v is not None},
        json=body,
        headers={"Accept": "application/json"},
    )


def call_raw(
    client: Any,
    method: str,
    path: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    body: Any = None,
) -> Any:
    """Sends a request the generated client has no operation for.

    The request goes through ``client.send_request``, so it gets the same
    authentication, endpoint and retry policies as a generated operation.
    """
    try:
        response = client.send_request(
            raw_request(method, path, params=params, body=body)
        )
        return parse_response(response)
    except HttpResponseError as err:
        raise to_sandbox_error(err) from err


def open_stream(client: Any, sandbox_id: str, pid: int) -> Any:
    """Opens the attach stream and returns the streaming HTTP response.

    The request is built by the generated request builder and sent through the
    client's own pipeline with ``stream=True``.
    """
    # pylint: disable=protected-access,import-outside-toplevel
    from pydo.operations._operations import build_sandboxes_get_commands_stream_request

    request = build_sandboxes_get_commands_stream_request(
        sandbox_id=sandbox_id, pid=pid, headers={"Accept": "application/json"}
    )
    request.url = client._client.format_url(request.url)
    return client._client._pipeline.run(request, stream=True).http_response


def open_exec(client: Any, sandbox_id: str, body: Any) -> Any:
    """Opens the exec stream and returns the streaming HTTP response.

    The request is built by the generated request builder and sent through the
    client's own pipeline with ``stream=True``: the generated operation would
    buffer the whole body.
    """
    # pylint: disable=protected-access,import-outside-toplevel
    from pydo.operations._operations import build_sandboxes_create_exec_request

    request = build_sandboxes_create_exec_request(
        sandbox_id=sandbox_id,
        json=body,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )
    request.url = client._client.format_url(request.url)
    return client._client._pipeline.run(request, stream=True).http_response


def keep_response(pipeline_response: Any, _deserialized: Any, _headers: Any) -> Any:
    """``cls`` callback for a binary operation: returns the status and raw response."""
    response = pipeline_response.http_response
    return response.status_code, response


def response_error(status: int, body: bytes, headers: Any) -> Any:
    """Builds the typed error for a binary operation's error response."""
    try:
        parsed = json.loads(body)
    except ValueError:
        parsed = None
    return build_error(status, parsed, None, headers)


def download(operation: Any, *args: Any, **kwargs: Any) -> bytes:
    """Runs a generated binary download and returns its whole body.

    The pipeline does not retry by status here (``retry_status=0``): the files
    facade retries a ``503`` itself, so it is not retried twice.
    """
    try:
        status, response = operation(*args, cls=keep_response, retry_status=0, **kwargs)
        body = response.read()
    except HttpResponseError as err:
        raise to_sandbox_error(err) from err
    if status >= 400:
        raise response_error(status, body, response.headers)
    return body
