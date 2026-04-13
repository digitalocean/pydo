"""Integration tests for inference endpoints.

These tests hit the live DigitalOcean serverless inference API. They require
a valid ``DIGITALOCEAN_TOKEN`` (or ``MODEL_ACCESS_KEY``) environment variable
with inference permissions.

All calls use the resource-level method names from ``src/pydo/resources/``:

* ``client.chat.completions.create(...)``   — inference/chat/completions.py
* ``client.models.list()``                  — inference/models.py
* ``client.images.generate(...)``           — inference/images/__init__.py
* ``client.responses.create(...)``          — inference/responses.py
* ``client.async_invoke.create(...)``       — inference/async_invoke.py
* ``client.async_images.generate(...)``     — inference/async_invoke.py (AsyncInvokeImages)
* ``client.audio.generate(...)``            — inference/async_invoke.py (AsyncInvokeAudio)
* ``client.audio.speech.create(...)``       — inference/async_invoke.py (AsyncInvokeSpeech)
* ``client.speech.create(...)``             — client_surface shortcut → audio.speech
* ``client.agent.chat.completions.create(...)`` — agent_inference/chat/completions.py

Agent inference tests additionally require ``AGENT_ENDPOINT`` and optionally
``AGENT_INFERENCE_TOKEN``.
"""

import os

import pytest

from pydo import Client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def inference_client() -> Client:
    """Client configured for serverless inference.

    Prefers ``MODEL_ACCESS_KEY`` but falls back to ``DIGITALOCEAN_TOKEN``.
    """
    token = os.environ.get("MODEL_ACCESS_KEY") or os.environ.get(
        "DIGITALOCEAN_TOKEN"
    )
    if not token:
        pytest.skip("MODEL_ACCESS_KEY or DIGITALOCEAN_TOKEN required")
    return Client(token)


@pytest.fixture(scope="module")
def agent_client() -> Client:
    """Client configured for agent inference.

    Requires ``AGENT_ENDPOINT``; token from ``AGENT_INFERENCE_TOKEN`` or
    ``MODEL_ACCESS_KEY`` or ``DIGITALOCEAN_TOKEN``.
    """
    agent_endpoint = os.environ.get("AGENT_ENDPOINT", "")
    if not agent_endpoint:
        pytest.skip("AGENT_ENDPOINT required for agent inference tests")

    token = (
        os.environ.get("AGENT_INFERENCE_TOKEN")
        or os.environ.get("MODEL_ACCESS_KEY")
        or os.environ.get("DIGITALOCEAN_TOKEN")
    )
    if not token:
        pytest.skip("Token required for agent inference tests")

    return Client(token, agent_endpoint=agent_endpoint)


# ---------------------------------------------------------------------------
# client.models.list  (inference/models.py)
# ---------------------------------------------------------------------------


class TestModelsList:
    """GET /v1/models via client.models.list()"""

    def test_models_list_returns_data(self, inference_client: Client):
        resp = inference_client.models.list()

        assert resp is not None
        assert resp.data is not None
        assert isinstance(resp.data, list)

    def test_models_list_entries_have_id(self, inference_client: Client):
        resp = inference_client.models.list()

        if len(resp.data) == 0:
            pytest.skip("No models available")

        model = resp.data[0]
        assert model.id is not None
        assert isinstance(model.id, str)
        assert len(model.id) > 0

    def test_models_list_dotdict_access(self, inference_client: Client):
        resp = inference_client.models.list()

        assert resp.data is not None
        if len(resp.data) > 0:
            assert resp.data[0].id is not None


# ---------------------------------------------------------------------------
# client.chat.completions.create  (inference/chat/completions.py)
# ---------------------------------------------------------------------------


class TestChatCompletionsCreate:
    """POST /v1/chat/completions via client.chat.completions.create()"""

    def test_basic_completion(self, inference_client: Client):
        resp = inference_client.chat.completions.create(
            model="llama3.3-70b-instruct",
            messages=[{"role": "user", "content": "Say hello in one word."}],
        )

        assert resp is not None
        assert len(resp.choices) >= 1
        assert resp.choices[0].message.role == "assistant"
        assert len(resp.choices[0].message.content) > 0

    def test_completion_with_system_message(self, inference_client: Client):
        resp = inference_client.chat.completions.create(
            model="llama3.3-70b-instruct",
            messages=[
                {"role": "system", "content": "You respond in exactly two words."},
                {"role": "user", "content": "Greet me."},
            ],
        )

        assert resp is not None
        assert len(resp.choices) >= 1
        assert len(resp.choices[0].message.content) > 0

    def test_completion_with_max_tokens(self, inference_client: Client):
        resp = inference_client.chat.completions.create(
            model="llama3.3-70b-instruct",
            messages=[{"role": "user", "content": "Count to 100."}],
            max_tokens=10,
        )

        assert resp is not None
        assert resp.usage is not None

    def test_completion_has_usage(self, inference_client: Client):
        resp = inference_client.chat.completions.create(
            model="llama3.3-70b-instruct",
            messages=[{"role": "user", "content": "Hi"}],
        )

        assert resp.usage.prompt_tokens > 0
        assert resp.usage.completion_tokens > 0
        assert resp.usage.total_tokens == (
            resp.usage.prompt_tokens + resp.usage.completion_tokens
        )


# ---------------------------------------------------------------------------
# client.chat.completions.create  — streaming
# ---------------------------------------------------------------------------


class TestChatCompletionsCreateStreaming:
    """POST /v1/chat/completions with stream=True"""

    def test_streaming_chat_completion(self, inference_client: Client):
        stream = inference_client.chat.completions.create(
            model="llama3.3-70b-instruct",
            messages=[{"role": "user", "content": "Say yes."}],
            stream=True,
            max_tokens=5,
        )

        chunks = []
        with stream:
            for chunk in stream:
                chunks.append(chunk)

        assert len(chunks) > 0
        assert chunks[0].get("object") == "chat.completion.chunk"


# ---------------------------------------------------------------------------
# client.images.generate  (inference/images/__init__.py → generations.py)
# ---------------------------------------------------------------------------


class TestImagesGenerate:
    """POST /v1/images/generations via client.images.generate()"""

    @pytest.mark.real_billing
    def test_images_generate(self, inference_client: Client):
        resp = inference_client.images.generate(
            model="openai-gpt-image-1",
            prompt="A simple red circle on white background",
            n=1,
        )

        assert resp is not None
        assert resp.data is not None
        assert len(resp.data) >= 1


# ---------------------------------------------------------------------------
# client.responses.create  (inference/responses.py)
# ---------------------------------------------------------------------------


class TestResponsesCreate:
    """POST /v1/responses via client.responses.create()"""

    def test_responses_create(self, inference_client: Client):
        resp = inference_client.responses.create(
            model="openai-gpt-oss-20b",
            input="What is 2+2? Reply with just the number.",
        )

        assert resp is not None
        assert resp.output is not None
        assert len(resp.output) >= 1

    def test_responses_create_with_instructions(self, inference_client: Client):
        resp = inference_client.responses.create(
            model="openai-gpt-oss-20b",
            input="Name a color.",
            instructions="Respond in one word only.",
        )

        assert resp is not None
        assert resp.output is not None

    def test_responses_create_streaming(self, inference_client: Client):
        stream = inference_client.responses.create(
            model="openai-gpt-oss-20b",
            input="Say hello.",
            stream=True,
        )

        chunks = []
        with stream:
            for chunk in stream:
                chunks.append(chunk)

        assert len(chunks) > 0


# ---------------------------------------------------------------------------
# client.async_invoke.create  (inference/async_invoke.py → AsyncInvoke)
# ---------------------------------------------------------------------------


class TestAsyncInvokeCreate:
    """POST /v1/async-invoke via client.async_invoke.create()"""

    @pytest.mark.real_billing
    def test_async_invoke_create(self, inference_client: Client):
        resp = inference_client.async_invoke.create(
            model_id="fal-ai/flux/schnell",
            input={"prompt": "A yellow star"},
        )

        assert resp is not None
        assert resp.request_id is not None
        assert resp.status in ("QUEUED", "IN_PROGRESS", "COMPLETED")


# ---------------------------------------------------------------------------
# client.async_images.generate  (inference/async_invoke.py → AsyncInvokeImages)
# ---------------------------------------------------------------------------


class TestAsyncImagesGenerate:
    """POST /v1/async-invoke via client.async_images.generate()"""

    @pytest.mark.real_billing
    def test_async_images_generate(self, inference_client: Client):
        resp = inference_client.async_images.generate(
            model_id="fal-ai/flux/schnell",
            prompt="A green triangle on a white background",
        )

        assert resp is not None
        assert resp.request_id is not None
        assert resp.status in ("QUEUED", "IN_PROGRESS", "COMPLETED")


# ---------------------------------------------------------------------------
# client.audio.generate  (inference/async_invoke.py → AsyncInvokeAudio)
# ---------------------------------------------------------------------------


class TestAudioGenerate:
    """POST /v1/async-invoke via client.audio.generate()"""

    @pytest.mark.real_billing
    def test_audio_generate(self, inference_client: Client):
        resp = inference_client.audio.generate(
            model_id="fal-ai/stable-audio-25/text-to-audio",
            prompt="A short drum beat",
            seconds_total=5,
        )

        assert resp is not None
        assert resp.request_id is not None
        assert resp.status in ("QUEUED", "IN_PROGRESS", "COMPLETED")


# ---------------------------------------------------------------------------
# client.audio.speech.create / client.speech.create
# (inference/async_invoke.py → AsyncInvokeSpeech)
# ---------------------------------------------------------------------------


class TestAudioSpeechCreate:
    """POST /v1/async-invoke via client.audio.speech.create() / client.speech.create()"""

    @pytest.mark.real_billing
    def test_audio_speech_create(self, inference_client: Client):
        resp = inference_client.audio.speech.create(
            input="Hello, this is a test.",
            model_id="fal-ai/elevenlabs/tts/multilingual-v2",
        )

        assert resp is not None
        assert resp.request_id is not None
        assert resp.status in ("QUEUED", "IN_PROGRESS", "COMPLETED")

    @pytest.mark.real_billing
    def test_speech_create_shortcut(self, inference_client: Client):
        resp = inference_client.speech.create(
            input="Testing the shortcut.",
            model_id="fal-ai/elevenlabs/tts/multilingual-v2",
        )

        assert resp is not None
        assert resp.request_id is not None
        assert resp.status in ("QUEUED", "IN_PROGRESS", "COMPLETED")


# ---------------------------------------------------------------------------
# client.agent.chat.completions.create
# (agent_inference/chat/completions.py)
# ---------------------------------------------------------------------------


class TestAgentChatCompletionsCreate:
    """Agent inference — POST /api/v1/chat/completions
    via client.agent.chat.completions.create()
    """

    def test_agent_chat_completions_create(self, agent_client: Client):
        model = os.environ.get("AGENT_MODEL", "gpt-4o")

        resp = agent_client.agent.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Reply in one word: hello or goodbye?"},
            ],
        )

        assert resp is not None
        assert len(resp.choices) >= 1
        assert len(resp.choices[0].message.content) > 0

    def test_agent_chat_completions_create_multi_turn(self, agent_client: Client):
        model = os.environ.get("AGENT_MODEL", "gpt-4o")

        resp = agent_client.agent.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Ping"},
            ],
            max_tokens=5,
        )

        assert resp is not None
        assert len(resp.choices) >= 1
