# pylint: disable=missing-function-docstring,protected-access,missing-class-docstring,too-few-public-methods
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Shared fakes for gateway tests — no network, fake pipeline plumbing."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, List, Optional
from unittest.mock import MagicMock

from pydo.aio.gateway import AsyncGatewayResources
from pydo.aio.gateway.custom_operations import AsyncRESTTransport
from pydo.custom_extensions import _BaseURLProxy
from pydo.gateway import GatewayResources, RESTTransport

TEST_SESSION_URN = "do:managed_agents_session:test-session"
TEST_GATEWAY_URL = "https://actions.do-ai-test.run"


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
    def __init__(self, status_code: int, body: Any = None):
        super().__init__(status_code, body)
        self.read_calls = 0

    async def read(self) -> bytes:  # pylint: disable=invalid-overridden-method
        self.read_calls += 1
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
    """MCP tools/call result shape (legacy helper for MCP-specific tests)."""
    result: dict = {"isError": is_error}
    if structured is not None:
        result["structuredContent"] = structured
    if text:
        result["content"] = [{"type": "text", "text": text}]
    return result


def tool_result(
    output: Any = None, *, error: Any = None, call_id: str = "call_1"
) -> dict:
    """REST ToolResult envelope (search / code)."""
    if error is not None:
        return {"status": "failed", "error": error, "call_id": call_id}
    return {"status": "succeeded", "output": output, "call_id": call_id}


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


def chat_tool_response(
    *,
    name: str = "web_search",
    arguments: str = '{"query": "do"}',
    call_id: str = "call_1",
) -> dict:
    """Build a chat-completions response containing one tool call."""
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": arguments,
                            },
                        }
                    ],
                }
            }
        ]
    }


def session_create_response(
    *,
    session_urn: str = TEST_SESSION_URN,
    end_user_id: str = "user-123",
    name: str = "test-session",
) -> dict:
    return {
        "session": {
            "sessionUrn": session_urn,
            "teamId": "42",
            "name": name,
            "policyJson": '{"defaultAction":"allow","rules":[]}',
            "endUserId": end_user_id,
        }
    }


def make_parent(responses: List[FakeResponse]) -> MagicMock:
    parent = MagicMock()
    parent._client = MagicMock()
    parent._client._pipeline = FakePipeline(responses)
    parent._client.format_url = lambda url, **_kwargs: (
        url if str(url).startswith("http") else f"https://api.digitalocean.com{url}"
    )
    return parent


def make_async_parent(responses: List[AsyncFakeResponse]) -> MagicMock:
    parent = MagicMock()
    parent._client = MagicMock()
    parent._client._pipeline = AsyncFakePipeline(responses)
    parent._client.format_url = lambda url, **_kwargs: (
        url if str(url).startswith("http") else f"https://api.digitalocean.com{url}"
    )
    return parent


def make_gateway(
    responses: List[FakeResponse],
    provider=None,
    *,
    session_id: str = TEST_SESSION_URN,
) -> GatewayResources:
    parent = make_parent(responses)
    proxy = _BaseURLProxy(parent._client, TEST_GATEWAY_URL)
    transport = RESTTransport(proxy, session_id=session_id)
    return GatewayResources(
        parent,
        gateway_endpoint=TEST_GATEWAY_URL,
        provider=provider,
        transport=transport,
    )


def make_async_gateway(
    responses: List[AsyncFakeResponse],
    provider=None,
    *,
    session_id: str = TEST_SESSION_URN,
) -> AsyncGatewayResources:
    parent = make_async_parent(responses)
    proxy = _BaseURLProxy(parent._client, TEST_GATEWAY_URL)
    transport = AsyncRESTTransport(proxy, session_id=session_id)
    return AsyncGatewayResources(
        parent,
        gateway_endpoint=TEST_GATEWAY_URL,
        provider=provider,
        transport=transport,
    )


def pipeline_of(gateway) -> Any:
    return gateway._transport._client._original._pipeline


def sent_request(gateway, index: int = 0) -> Any:
    return pipeline_of(gateway).calls[index].request


def sent_payload(gateway, index: int = 0) -> Optional[dict]:
    request = sent_request(gateway, index)
    content = request.content
    if content is None:
        return None
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    if not content:
        return None
    return json.loads(content)
