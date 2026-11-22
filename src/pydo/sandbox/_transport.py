# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""How the sync sandbox SDK calls the generated operations.

Hand-written; preserved across ``make generate``.
"""

from typing import Any

from azure.core.exceptions import HttpResponseError

from .errors import build_error, to_sandbox_error, unwrap, with_response


def guard_response(pipeline_response: Any) -> None:
    """``raw_response_hook``: every sandbox endpoint answers JSON.

    Any other content type means something else replied (a gateway's HTML 404 or
    502 page, a route that is not deployed). The generated operation would fail
    on it with a bare JSON decode error that hides the status, so raise the usual
    typed error with the status and the start of the body instead.
    """
    response = pipeline_response.http_response
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
