# pylint: disable=missing-class-docstring,missing-function-docstring
# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Tests for SSE stream transport and decode error handling."""

import asyncio

import pytest

from pydo.custom_extensions import (
    AsyncSSEStream,
    SSEStream,
    async_iter_sse_with_retry,
    iter_sse_with_retry,
)
from pydo.exceptions import (
    SSEStreamDecodeError,
    SSEStreamRetryExhaustedError,
    SSEStreamTransportError,
)


class _SyncBytes:
    def __init__(self, chunks):
        self._chunks = list(chunks)

    def iter_bytes(self):
        yield from self._chunks

    def close(self):
        pass


class _FailingBytes:
    def iter_bytes(self):
        yield b'data: {"ok": true}\n\n'
        raise ConnectionResetError("reset")

    def close(self):
        pass


class _TruncatedBytes:
    def iter_bytes(self):
        yield b"data: {"

    def close(self):
        pass


def test_sse_stream_happy_path():
    body = b'data: {"x": 1}\n\n' b'data: {"x": 2}\n\n' b"data: [DONE]\n\n"
    stream = SSEStream(_SyncBytes([body]))
    assert list(stream) == [{"x": 1}, {"x": 2}]


def test_sse_stream_invalid_json_raises():
    stream = SSEStream(_SyncBytes([b"data: not-json\n\n"]))
    with pytest.raises(SSEStreamDecodeError, match="invalid JSON"):
        list(stream)


def test_sse_stream_truncated_line_raises():
    stream = SSEStream(_TruncatedBytes())
    with pytest.raises(SSEStreamTransportError, match="incomplete line"):
        list(stream)


def test_sse_stream_connection_error_wrapped():
    stream = SSEStream(_FailingBytes())
    with pytest.raises(SSEStreamTransportError, match="interrupted"):
        list(stream)


def test_async_sse_stream_invalid_json_raises():
    class _AsyncBytes:
        async def iter_bytes(self):
            yield b"data: not-json\n\n"

        def close(self):
            pass

    async def _consume() -> None:
        stream = AsyncSSEStream(_AsyncBytes())
        async for _ in stream:  # noqa: F841
            pass

    with pytest.raises(SSEStreamDecodeError, match="invalid JSON"):
        asyncio.run(_consume())


class _FailBeforeYield:
    def iter_bytes(self):
        raise ConnectionResetError("before any chunk")

    def close(self):
        pass


def test_iter_sse_with_retry_recover_before_first_chunk():
    calls = []

    def factory():
        calls.append(len(calls))
        if len(calls) == 1:
            return SSEStream(_FailBeforeYield())
        body = b'data: {"recovered": true}\n\n' b"data: [DONE]\n\n"
        return SSEStream(_SyncBytes([body]))

    chunks = list(iter_sse_with_retry(factory, max_attempts=3))
    assert chunks == [{"recovered": True}]
    assert len(calls) == 2


def test_iter_sse_with_retry_exhausted():
    def factory():
        return SSEStream(_FailBeforeYield())

    with pytest.raises(SSEStreamRetryExhaustedError, match="after 2 attempt"):
        list(iter_sse_with_retry(factory, max_attempts=2))


def test_async_iter_sse_with_retry_recover_before_first_chunk():
    calls = []

    def factory():
        calls.append(len(calls))
        if len(calls) == 1:
            return AsyncSSEStream(_FailBeforeYield())
        body = b'data: {"recovered": true}\n\n' b"data: [DONE]\n\n"

        class _AsyncOk:
            async def iter_bytes(self):
                yield body

            def close(self):
                pass

        return AsyncSSEStream(_AsyncOk())

    async def _run():
        out = []
        async for chunk in async_iter_sse_with_retry(factory, max_attempts=3):
            out.append(chunk)
        return out

    chunks = asyncio.run(_run())
    assert chunks == [{"recovered": True}]
    assert len(calls) == 2


@pytest.mark.parametrize("with_bom", [False, True])
@pytest.mark.parametrize("chunk_size", [1, 2, 1000])
@pytest.mark.parametrize("is_async", [False, True])
def test_sse_stream_preserves_first_event_with_optional_bom(
    with_bom, chunk_size, is_async
):
    payload = (
        'data: {"text": "雪\ufeff"}\n\ndata: {"last": true}\n\ndata: [DONE]\n\n'.encode(
            "utf-8"
        )
    )
    if with_bom:
        payload = b"\xef\xbb\xbf" + payload
    chunks = [payload[i : i + chunk_size] for i in range(0, len(payload), chunk_size)]
    expected = [{"text": "雪\ufeff"}, {"last": True}]
    if is_async:

        class AsyncBytes:
            async def iter_bytes(self):
                for chunk in chunks:
                    yield chunk

        async def consume():
            return [event async for event in AsyncSSEStream(AsyncBytes())]

        result = asyncio.run(consume())
    else:
        result = list(SSEStream(_SyncBytes(chunks)))
    assert result == expected
