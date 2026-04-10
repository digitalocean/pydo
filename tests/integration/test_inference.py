# pylint: disable=duplicate-code

"""test_inference.py
    Integration tests for serverless inference endpoints.
"""

import json
import time
from os import environ

import pytest
import requests

from pydo import Client
from pydo.aio import Client as AsyncClient
from pydo.custom_extensions import DotDict, SSEStream, AsyncSSEStream

INFERENCE_URL = "https://inference.do-ai.run"

CHAT_MODEL = "minimax-m2.5"
RESPONSES_MODEL = "openai-gpt-oss-20b"
IMAGE_MODEL = "fal-ai/fast-sdxl"
AUDIO_MODEL = "fal-ai/stable-audio-25/text-to-audio"
TTS_MODEL = "fal-ai/elevenlabs/tts/multilingual-v2"


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def inference_token():
    token = environ.get("MODEL_ACCESS_KEY")
    if token is None:
        pytest.skip("MODEL_ACCESS_KEY not set")
    return token


@pytest.fixture(scope="module")
def inference_client(inference_token):
    return Client(inference_token)


@pytest.fixture
def async_client(inference_token):
    """Function-scoped async client so each test gets a fresh event loop."""
    return AsyncClient(inference_token)


# ── List Models ───────────────────────────────────────────────────────────


class TestListModels:
    def test_list_models_sync(self, inference_client):
        """GET /v1/models returns a list of available models."""
        response = inference_client.models.list()

        assert isinstance(response, DotDict)
        assert hasattr(response, "data")
        assert isinstance(response.data, list)
        assert len(response.data) > 0

        model = response.data[0]
        assert hasattr(model, "id")
        assert isinstance(model.id, str)
        assert len(model.id) > 0

    @pytest.mark.asyncio
    async def test_list_models_async(self, async_client):
        """GET /v1/models (async) returns a list of available models."""
        response = await async_client.models.list()

        assert isinstance(response, DotDict)
        assert hasattr(response, "data")
        assert len(response.data) > 0
        assert hasattr(response.data[0], "id")

        await async_client.close()


# ── Chat Completions ─────────────────────────────────────────────────────


class TestChatCompletions:
    def test_chat_completion_sync(self, inference_client):
        """POST /v1/chat/completions returns a valid completion."""
        completion = inference_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "user", "content": "Say hello in exactly one word."},
            ],
        )

        assert isinstance(completion, DotDict)
        assert hasattr(completion, "choices")
        assert len(completion.choices) > 0

        choice = completion.choices[0]
        assert hasattr(choice, "message")
        assert hasattr(choice.message, "content")
        assert isinstance(choice.message.content, str)
        assert len(choice.message.content) > 0

    def test_chat_completion_streaming_sync(self, inference_client):
        """POST /v1/chat/completions with stream=True returns SSE chunks."""
        stream = inference_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "user", "content": "Count from 1 to 3."},
            ],
            stream=True,
        )

        assert isinstance(stream, SSEStream)

        chunks = []
        with stream:
            for chunk in stream:
                assert isinstance(chunk, DotDict)
                chunks.append(chunk)

        assert len(chunks) > 0
        assert any(
            hasattr(c, "choices") and len(c.choices) > 0
            for c in chunks
        )

    @pytest.mark.asyncio
    async def test_chat_completion_async(self, async_client):
        """POST /v1/chat/completions (async) returns a valid completion."""
        completion = await async_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "user", "content": "Say hello in exactly one word."},
            ],
        )

        assert isinstance(completion, DotDict)
        assert len(completion.choices) > 0
        assert len(completion.choices[0].message.content) > 0

        await async_client.close()

    @pytest.mark.asyncio
    async def test_chat_completion_streaming_async(self, async_client):
        """POST /v1/chat/completions with stream=True (async) returns SSE chunks."""
        stream = await async_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "user", "content": "Count from 1 to 3."},
            ],
            stream=True,
        )

        assert isinstance(stream, AsyncSSEStream)

        chunks = []
        async with stream:
            async for chunk in stream:
                assert isinstance(chunk, DotDict)
                chunks.append(chunk)

        assert len(chunks) > 0

        await async_client.close()


# ── Responses ─────────────────────────────────────────────────────────────


class TestResponses:
    @pytest.mark.asyncio
    async def test_responses_non_streaming(self, async_client):
        """POST /v1/responses returns a text response."""
        result = await async_client.responses.create(
            model=RESPONSES_MODEL,
            input="What is 2 + 2? Reply with the number only.",
        )

        assert isinstance(result, DotDict)
        assert hasattr(result, "id")

        await async_client.close()

    @pytest.mark.asyncio
    async def test_responses_streaming(self, async_client):
        """POST /v1/responses with stream=True returns SSE events."""
        stream = await async_client.responses.create(
            model=RESPONSES_MODEL,
            input="Say hello.",
            stream=True,
        )

        assert isinstance(stream, AsyncSSEStream)

        chunks = []
        async with stream:
            async for event in stream:
                assert isinstance(event, DotDict)
                assert hasattr(event, "type")
                chunks.append(event)

        assert len(chunks) > 0
        event_types = {c.type for c in chunks}
        assert len(event_types) > 0

        await async_client.close()


# ── Image Generation (async-invoke) ──────────────────────────────────────


class TestImageGeneration:
    def test_image_generation_queued(self, inference_client):
        """POST /v1/async-invoke for image gen returns a queued job."""
        result = inference_client.async_invoke.images.generate(
            model_id=IMAGE_MODEL,
            prompt="A simple red circle on a white background.",
        )

        assert isinstance(result, DotDict)
        assert hasattr(result, "request_id")
        assert result.request_id is not None
        assert len(result.request_id) > 0

    def test_image_generation_poll_completes(self, inference_token, inference_client):
        """Submit image gen and poll until COMPLETED or timeout."""
        result = inference_client.async_invoke.images.generate(
            model_id=IMAGE_MODEL,
            prompt="A blue square.",
        )
        request_id = result.request_id
        assert request_id

        headers = {"Authorization": f"Bearer {inference_token}"}
        deadline = time.time() + 90

        while time.time() < deadline:
            time.sleep(5)
            resp = requests.get(
                f"{INFERENCE_URL}/v1/async-invoke/{request_id}",
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("output") is not None:
                    assert "images" in data["output"]
                    assert len(data["output"]["images"]) > 0
                    assert "url" in data["output"]["images"][0]
                    return

        pytest.fail(f"Image generation did not complete within 90s (request_id={request_id})")


# ── Audio Generation (async-invoke) ──────────────────────────────────────


class TestAudioGeneration:
    def test_audio_generation_queued(self, inference_client):
        """POST /v1/async-invoke for audio gen returns a queued job."""
        result = inference_client.async_invoke.audio.generate(
            model_id=AUDIO_MODEL,
            prompt="A gentle rain sound effect",
            seconds_total=5,
        )

        assert isinstance(result, DotDict)
        assert hasattr(result, "request_id")
        assert result.request_id is not None


# ── Text-to-Speech (async-invoke) ────────────────────────────────────────


class TestTextToSpeech:
    def test_tts_queued(self, inference_client):
        """POST /v1/async-invoke for TTS returns a queued job."""
        result = inference_client.async_invoke.audio.speech.create(
            model_id=TTS_MODEL,
            input="Hello world.",
        )

        assert isinstance(result, DotDict)
        assert hasattr(result, "request_id")
        assert result.request_id is not None


# ── Async-Invoke Polling ─────────────────────────────────────────────────


class TestAsyncInvokePoll:
    def test_poll_returns_result_for_completed_job(self, inference_token, inference_client):
        """GET /v1/async-invoke/{request_id} returns output for a completed job.

        Submits a fast image generation, waits for completion, then verifies
        the GET endpoint returns output data.
        """
        result = inference_client.async_invoke.images.generate(
            model_id=IMAGE_MODEL,
            prompt="A green triangle.",
        )
        request_id = result.request_id

        headers = {"Authorization": f"Bearer {inference_token}"}
        deadline = time.time() + 90

        while time.time() < deadline:
            time.sleep(5)
            resp = requests.get(
                f"{INFERENCE_URL}/v1/async-invoke/{request_id}",
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("output") is not None:
                    assert data["request_id"] == request_id
                    assert data["output"] is not None
                    return

        pytest.fail(
            f"Polling did not return completed result within 90s "
            f"(request_id={request_id})"
        )


# ── DotDict Access ────────────────────────────────────────────────────────


class TestDotDictAccess:
    def test_chat_completion_dot_access(self, inference_client):
        """Verify responses support dot notation access."""
        completion = inference_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "user", "content": "Say OK."},
            ],
        )

        content = completion.choices[0].message.content
        assert isinstance(content, str)
        assert len(content) > 0

        content_dict = completion["choices"][0]["message"]["content"]
        assert content == content_dict

    def test_list_models_dot_access(self, inference_client):
        """Verify model list supports dot notation."""
        response = inference_client.models.list()

        model_id_dot = response.data[0].id
        model_id_dict = response["data"][0]["id"]
        assert model_id_dot == model_id_dict
