# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""How the async sandbox SDK calls the generated operations.

Hand-written; preserved across ``make generate``.
"""

from typing import Any

from azure.core.exceptions import HttpResponseError

from pydo.sandbox._transport import guard_response
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
