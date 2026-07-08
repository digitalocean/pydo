# pylint: disable=missing-function-docstring,protected-access,missing-class-docstring,too-few-public-methods
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Shared fakes for gateway tests — no network, fake pipeline plumbing."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import MagicMock

from pydo.gateway import GatewayResources
from pydo.aio.gateway import AsyncGatewayResources


class FakeResponse:
    def __init__(self, status_code: int, body: Any = None):
        self.status_code = status_code
        self.reason = ""
        self.headers: dict = {}
        if isinstance(body, (dict, list)):
            self._body_bytes = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            self._body_bytes = body.encode("utf-8")
        elif isinstance(body, bytes):
            self._body_bytes = body
        else:
            self._body_bytes = b""

    def text(self) -> str:
        return self._body_bytes.decode("utf-8")

    def body(self) -> bytes:
        return self._body_bytes

    def read(self) -> bytes:
        return self._body_bytes

    def close(self) -> None:
        pass


class AsyncFakeResponse(FakeResponse):
    async def read(self) -> bytes:  # pylint: disable=invalid-overridden-method
        return self._body_bytes


class FakePipeline:
    def __init__(self, responses: List[FakeResponse]):
        self._responses = list(responses)
        self.calls: List[Any] = []

    def run(self, request, *, stream=False):
        self.calls.append(SimpleNamespace(request=request, stream=stream))
        return SimpleNamespace(http_response=self._responses.pop(0))


class AsyncFakePipeline:
    def __init__(self, responses: List[AsyncFakeResponse]):
        self._responses = list(responses)
        self.calls: List[Any] = []

    async def run(self, request, *, stream=False):
        self.calls.append(SimpleNamespace(request=request, stream=stream))
        return SimpleNamespace(http_response=self._responses.pop(0))


def jsonrpc_result(result: Any, *, rpc_id: int = 1) -> dict:
    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


def jsonrpc_error(code: int, message: str, *, rpc_id: int = 1) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "error": {"code": code, "message": message},
    }


def call_result(
    structured: Any = None, *, is_error: bool = False, text: str = ""
) -> dict:
    result: dict = {"isError": is_error}
    if structured is not None:
        result["structuredContent"] = structured
    if text:
        result["content"] = [{"type": "text", "text": text}]
    return result


def invoke_envelope(
    results: List[dict] | None = None,
    *,
    tool: str = "web_search",
    output: Any = None,
    error: Any = None,
    invocation_id: str | None = None,
) -> dict:
    """Build a gateway ``action_invoke`` result envelope for tests."""
    if results is None:
        if error is not None:
            result_body: dict = {"status": "failed", "error": error}
        else:
            if output is None:
                output = {"answer": 1}
            result_body = {"status": "succeeded", "output": output}
        entry: dict = {"index": 0, "tool": tool, "result": result_body}
        if invocation_id is not None:
            entry["invocation_id"] = invocation_id
        results = [entry]
    return {
        "total_count": len(results),
        "success_count": sum(
            1 for item in results if item["result"].get("status") == "succeeded"
        ),
        "error_count": sum(
            1 for item in results if item["result"].get("status") != "succeeded"
        ),
        "results": results,
    }


def make_gateway(responses: List[FakeResponse], provider=None) -> GatewayResources:
    parent = MagicMock()
    parent._client = MagicMock()
    parent._client._pipeline = FakePipeline(responses)
    return GatewayResources(
        parent,
        gateway_endpoint="https://actions.do-ai-test.run",
        provider=provider,
    )


def make_async_gateway(
    responses: List[AsyncFakeResponse], provider=None
) -> AsyncGatewayResources:
    parent = MagicMock()
    parent._client = MagicMock()
    parent._client._pipeline = AsyncFakePipeline(responses)
    return AsyncGatewayResources(
        parent,
        gateway_endpoint="https://actions.do-ai-test.run",
        provider=provider,
    )


def pipeline_of(gateway) -> Any:
    return gateway._transport._client._original._pipeline


def sent_request(gateway, index: int = 0) -> Any:
    return pipeline_of(gateway).calls[index].request


def sent_payload(gateway, index: int = 0) -> dict:
    request = sent_request(gateway, index)
    content = request.content
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    return json.loads(content)
