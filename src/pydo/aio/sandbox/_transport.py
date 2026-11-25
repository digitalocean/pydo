# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""How the async sandbox SDK calls the generated operations.

Hand-written; preserved across ``make generate``.
"""

from typing import Any

from azure.core.exceptions import HttpResponseError

from pydo.sandbox._transport import guard_response, keep_response, response_error
from pydo.sandbox.errors import to_sandbox_error, unwrap, with_response


async def call(operation: Any, *args: Any, **kwargs: Any) -> Any:
    """Runs a generated operation and raises a typed error for any failure."""
    try:
        return unwrap(
            await operation(
                *args,
                cls=with_response,
                raw_response_hook=guard_response,
                **kwargs,
            )
        )
    except HttpResponseError as err:
        raise to_sandbox_error(err) from err


async def open_stream(client: Any, sandbox_id: str, pid: int) -> Any:
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
    return (await client._client._pipeline.run(request, stream=True)).http_response


async def open_exec(client: Any, sandbox_id: str, body: Any) -> Any:
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
    return (await client._client._pipeline.run(request, stream=True)).http_response


async def download(operation: Any, *args: Any, **kwargs: Any) -> bytes:
    """Runs a generated binary download and returns its whole body.

    The pipeline does not retry by status here (``retry_status=0``): the files
    facade retries a ``503`` itself, so it is not retried twice.
    """
    try:
        status, response = await operation(
            *args, cls=keep_response, retry_status=0, **kwargs
        )
        body = await response.read()
    except HttpResponseError as err:
        raise to_sandbox_error(err) from err
    if status >= 400:
        raise response_error(status, body, response.headers)
    return body
