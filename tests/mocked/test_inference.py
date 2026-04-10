"""Mock tests for inference API resources.

These tests mock HTTP responses so they run without network access or tokens.
"""

import pytest
import responses
from aioresponses import aioresponses

from pydo import Client
from pydo.aio import Client as aioClient
from pydo.custom_extensions import DotDict, SSEStream, AsyncSSEStream

INFERENCE_URL = "https://inference.do-ai.run"


# ── Response fixtures ─────────────────────────────────────────────────────


CHAT_COMPLETION_RESPONSE = {
    "id": "chatcmpl-test123",
    "object": "chat.completion",
    "model": "minimax-m2.5",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Hello!",
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
}

CHAT_COMPLETION_STREAM_BODY = (
    b'data: {"id":"chatcmpl-s1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}\n\n'
    b'data: {"id":"chatcmpl-s1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":"stop"}]}\n\n'
    b"data: [DONE]\n\n"
)

LIST_MODELS_RESPONSE = {
    "object": "list",
    "data": [
        {"id": "minimax-m2.5", "object": "model", "owned_by": "digitalocean"},
        {"id": "deepseek-r1", "object": "model", "owned_by": "digitalocean"},
    ],
}

RESPONSES_RESPONSE = {
    "id": "resp-test456",
    "object": "response",
    "model": "openai-gpt-oss-20b",
    "output": [
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "4"}],
        }
    ],
}

RESPONSES_STREAM_BODY = (
    b'data: {"type":"response.created","response":{"id":"resp-s1"}}\n\n'
    b'data: {"type":"response.output_text.delta","delta":"Hello"}\n\n'
    b'data: {"type":"response.completed","response":{"id":"resp-s1"}}\n\n'
    b"data: [DONE]\n\n"
)

ASYNC_INVOKE_RESPONSE = {
    "completed_at": None,
    "created_at": "2026-04-09T16:00:00Z",
    "error": None,
    "model_id": "fal-ai/fast-sdxl",
    "output": None,
    "request_id": "test-request-id-123",
    "started_at": None,
    "status": "QUEUED",
}


# ── Client fixtures ───────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def inference_client():
    return Client("fake-token", inference_endpoint=INFERENCE_URL)


@pytest.fixture(scope="module")
def aio_inference_client():
    return aioClient("fake-token", inference_endpoint=INFERENCE_URL)


# ── List Models ───────────────────────────────────────────────────────────


class TestListModelsMocked:
    @responses.activate
    def test_list_models(self, inference_client):
        responses.add(
            responses.GET,
            f"{INFERENCE_URL}/v1/models",
            json=LIST_MODELS_RESPONSE,
            status=200,
        )

        result = inference_client.models.list()

        assert isinstance(result, DotDict)
        assert len(result.data) == 2
        assert result.data[0].id == "minimax-m2.5"
        assert result.data[1].id == "deepseek-r1"

    @pytest.mark.asyncio
    async def test_list_models_async(self, aio_inference_client):
        with aioresponses() as mock:
            mock.get(
                f"{INFERENCE_URL}/v1/models",
                payload=LIST_MODELS_RESPONSE,
                status=200,
            )

            result = await aio_inference_client.models.list()

            assert isinstance(result, DotDict)
            assert len(result.data) == 2
            assert result.data[0].id == "minimax-m2.5"


# ── Chat Completions ─────────────────────────────────────────────────────


class TestChatCompletionsMocked:
    @responses.activate
    def test_chat_completion(self, inference_client):
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/chat/completions",
            json=CHAT_COMPLETION_RESPONSE,
            status=200,
        )

        completion = inference_client.chat.completions.create(
            model="minimax-m2.5",
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert isinstance(completion, DotDict)
        assert completion.choices[0].message.content == "Hello!"
        assert completion.choices[0].message.role == "assistant"
        assert completion.id == "chatcmpl-test123"
        assert completion.usage.total_tokens == 15

    @responses.activate
    def test_chat_completion_dot_and_dict_access(self, inference_client):
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/chat/completions",
            json=CHAT_COMPLETION_RESPONSE,
            status=200,
        )

        completion = inference_client.chat.completions.create(
            model="minimax-m2.5",
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert completion.choices[0].message.content == completion["choices"][0]["message"]["content"]
        assert completion.model == completion["model"]

    @responses.activate
    def test_chat_completion_streaming(self, inference_client):
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/chat/completions",
            body=CHAT_COMPLETION_STREAM_BODY,
            status=200,
            content_type="text/event-stream",
            stream=True,
        )

        stream = inference_client.chat.completions.create(
            model="minimax-m2.5",
            messages=[{"role": "user", "content": "Hello"}],
            stream=True,
        )

        assert isinstance(stream, SSEStream)
        chunks = list(stream)
        assert len(chunks) == 2
        assert isinstance(chunks[0], DotDict)
        assert chunks[0].choices[0].delta.content == "Hello"
        assert chunks[1].choices[0].delta.content == "!"

    @pytest.mark.asyncio
    async def test_chat_completion_async(self, aio_inference_client):
        with aioresponses() as mock:
            mock.post(
                f"{INFERENCE_URL}/v1/chat/completions",
                payload=CHAT_COMPLETION_RESPONSE,
                status=200,
            )

            completion = await aio_inference_client.chat.completions.create(
                model="minimax-m2.5",
                messages=[{"role": "user", "content": "Hello"}],
            )

            assert isinstance(completion, DotDict)
            assert completion.choices[0].message.content == "Hello!"

    @responses.activate
    def test_chat_completion_sends_correct_body(self, inference_client):
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/chat/completions",
            json=CHAT_COMPLETION_RESPONSE,
            status=200,
        )

        inference_client.chat.completions.create(
            model="minimax-m2.5",
            messages=[{"role": "user", "content": "test"}],
            temperature=0.7,
        )

        import json
        sent = json.loads(responses.calls[0].request.body)
        assert sent["model"] == "minimax-m2.5"
        assert sent["messages"] == [{"role": "user", "content": "test"}]
        assert sent["temperature"] == 0.7


# ── Responses ─────────────────────────────────────────────────────────────


class TestResponsesMocked:
    @responses.activate
    def test_responses_create(self, inference_client):
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/responses",
            json=RESPONSES_RESPONSE,
            status=200,
        )

        result = inference_client.responses.create(
            model="openai-gpt-oss-20b",
            input="What is 2 + 2?",
        )

        assert isinstance(result, DotDict)
        assert result.id == "resp-test456"

    @responses.activate
    def test_responses_streaming(self, inference_client):
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/responses",
            body=RESPONSES_STREAM_BODY,
            status=200,
            content_type="text/event-stream",
            stream=True,
        )

        stream = inference_client.responses.create(
            model="openai-gpt-oss-20b",
            input="Say hello.",
            stream=True,
        )

        assert isinstance(stream, SSEStream)
        chunks = list(stream)
        assert len(chunks) == 3
        assert chunks[0].type == "response.created"
        assert chunks[1].type == "response.output_text.delta"
        assert chunks[1].delta == "Hello"
        assert chunks[2].type == "response.completed"


# ── Async Invoke (Image, Audio, TTS) ─────────────────────────────────────


class TestAsyncInvokeMocked:
    @responses.activate
    def test_image_generation_queued(self, inference_client):
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/async-invoke",
            json=ASYNC_INVOKE_RESPONSE,
            status=200,
        )

        result = inference_client.async_invoke.images.generate(
            model_id="fal-ai/fast-sdxl",
            prompt="A red circle.",
        )

        assert isinstance(result, DotDict)
        assert result.request_id == "test-request-id-123"
        assert result.status == "QUEUED"

    @responses.activate
    def test_image_generation_sends_correct_body(self, inference_client):
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/async-invoke",
            json=ASYNC_INVOKE_RESPONSE,
            status=200,
        )

        inference_client.async_invoke.images.generate(
            model_id="fal-ai/fast-sdxl",
            prompt="A red circle.",
        )

        import json
        sent = json.loads(responses.calls[0].request.body)
        assert sent["model_id"] == "fal-ai/fast-sdxl"
        assert sent["input"]["prompt"] == "A red circle."

    @responses.activate
    def test_audio_generation_queued(self, inference_client):
        audio_response = {**ASYNC_INVOKE_RESPONSE, "model_id": "fal-ai/stable-audio-25/text-to-audio"}
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/async-invoke",
            json=audio_response,
            status=200,
        )

        result = inference_client.async_invoke.audio.generate(
            model_id="fal-ai/stable-audio-25/text-to-audio",
            prompt="Rain sounds",
            seconds_total=5,
        )

        assert isinstance(result, DotDict)
        assert result.request_id == "test-request-id-123"

    @responses.activate
    def test_audio_generation_sends_correct_body(self, inference_client):
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/async-invoke",
            json=ASYNC_INVOKE_RESPONSE,
            status=200,
        )

        inference_client.async_invoke.audio.generate(
            model_id="fal-ai/stable-audio-25/text-to-audio",
            prompt="Rain sounds",
            seconds_total=30,
        )

        import json
        sent = json.loads(responses.calls[0].request.body)
        assert sent["model_id"] == "fal-ai/stable-audio-25/text-to-audio"
        assert sent["input"]["prompt"] == "Rain sounds"
        assert sent["input"]["seconds_total"] == 30

    @responses.activate
    def test_tts_queued(self, inference_client):
        tts_response = {**ASYNC_INVOKE_RESPONSE, "model_id": "fal-ai/elevenlabs/tts/multilingual-v2"}
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/async-invoke",
            json=tts_response,
            status=200,
        )

        result = inference_client.async_invoke.audio.speech.create(
            model_id="fal-ai/elevenlabs/tts/multilingual-v2",
            input="Hello world.",
        )

        assert isinstance(result, DotDict)
        assert result.request_id == "test-request-id-123"

    @responses.activate
    def test_tts_sends_correct_body(self, inference_client):
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/async-invoke",
            json=ASYNC_INVOKE_RESPONSE,
            status=200,
        )

        inference_client.async_invoke.audio.speech.create(
            model_id="fal-ai/elevenlabs/tts/multilingual-v2",
            input="Hello world.",
        )

        import json
        sent = json.loads(responses.calls[0].request.body)
        assert sent["model_id"] == "fal-ai/elevenlabs/tts/multilingual-v2"
        assert sent["input"]["text"] == "Hello world."

    @pytest.mark.asyncio
    async def test_async_invoke_async(self, aio_inference_client):
        with aioresponses() as mock:
            mock.post(
                f"{INFERENCE_URL}/v1/async-invoke",
                payload=ASYNC_INVOKE_RESPONSE,
                status=200,
            )

            result = await aio_inference_client.async_invoke.audio.speech.create(
                model_id="fal-ai/elevenlabs/tts/multilingual-v2",
                input="Hello.",
            )

            assert isinstance(result, DotDict)
            assert result.request_id == "test-request-id-123"


# ── Error handling ────────────────────────────────────────────────────────


class TestInferenceErrorsMocked:
    @responses.activate
    def test_model_not_found_404(self, inference_client):
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/chat/completions",
            json={"error": {"message": "model not found", "type": "not_found_error"}},
            status=404,
        )

        from azure.core.exceptions import ResourceNotFoundError
        with pytest.raises(ResourceNotFoundError):
            inference_client.chat.completions.create(
                model="nonexistent-model",
                messages=[{"role": "user", "content": "hi"}],
            )

    @responses.activate
    def test_auth_error_401(self, inference_client):
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/chat/completions",
            json={"error": {"message": "invalid token"}},
            status=401,
        )

        from azure.core.exceptions import ClientAuthenticationError
        with pytest.raises(ClientAuthenticationError):
            inference_client.chat.completions.create(
                model="minimax-m2.5",
                messages=[{"role": "user", "content": "hi"}],
            )

    @responses.activate
    def test_server_error_500(self, inference_client):
        responses.add(
            responses.POST,
            f"{INFERENCE_URL}/v1/async-invoke",
            json={"error": {"message": "internal server error"}},
            status=500,
        )

        from azure.core.exceptions import HttpResponseError
        with pytest.raises(HttpResponseError):
            inference_client.async_invoke.images.generate(
                model_id="fal-ai/fast-sdxl",
                prompt="test",
            )


# ── DotDict unit tests ───────────────────────────────────────────────────


class TestDotDict:
    def test_basic_access(self):
        d = DotDict({"a": 1, "b": "hello"})
        assert d.a == 1
        assert d.b == "hello"
        assert d["a"] == 1

    def test_nested_access(self):
        from pydo.custom_extensions import _wrap
        d = _wrap({"choices": [{"message": {"content": "hi"}}]})
        assert d.choices[0].message.content == "hi"

    def test_missing_attr_raises(self):
        d = DotDict({"a": 1})
        with pytest.raises(AttributeError, match="no_such"):
            _ = d.no_such

    def test_dict_compatibility(self):
        d = DotDict({"x": 1, "y": 2})
        assert "x" in d
        assert d.get("z", 99) == 99
        assert list(d.keys()) == ["x", "y"]

    def test_json_serializable(self):
        import json
        d = DotDict({"a": [1, 2], "b": {"c": 3}})
        roundtrip = json.loads(json.dumps(d))
        assert roundtrip == {"a": [1, 2], "b": {"c": 3}}
