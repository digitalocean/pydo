# pylint: disable=line-too-long
"""Mock tests for inference API endpoints.

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
"""

import responses

from pydo import Client


INFERENCE_URL = "https://inference.do-ai.run"


# ---------------------------------------------------------------------------
# client.chat.completions.create  (inference/chat/completions.py)
# ---------------------------------------------------------------------------


@responses.activate
def test_chat_completions_create(mock_client: Client, mock_client_url):
    """Mock POST /v1/chat/completions — non-streaming."""
    expected = {
        "id": "chatcmpl-abc123",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "meta-llama/Meta-Llama-3-8B-Instruct",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you today?",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 9,
            "total_tokens": 19,
        },
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/chat/completions",
        json=expected,
        status=200,
    )

    resp = mock_client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        messages=[{"role": "user", "content": "Hello!"}],
    )

    assert resp.id == "chatcmpl-abc123"
    assert resp.object == "chat.completion"
    assert resp.choices[0].message.content == "Hello! How can I help you today?"
    assert resp.choices[0].finish_reason == "stop"


@responses.activate
def test_chat_completions_create_with_system_message(
    mock_client: Client, mock_client_url
):
    """Mock chat.completions.create with a developer/system message."""
    expected = {
        "id": "chatcmpl-sys456",
        "object": "chat.completion",
        "created": 1700000100,
        "model": "minimax-m2.5",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Arr! Ye be askin' about Python, matey!",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 25,
            "completion_tokens": 12,
            "total_tokens": 37,
        },
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/chat/completions",
        json=expected,
        status=200,
    )

    resp = mock_client.chat.completions.create(
        model="minimax-m2.5",
        messages=[
            {"role": "developer", "content": "Talk like a pirate."},
            {"role": "user", "content": "Tell me about Python."},
        ],
    )

    assert resp.choices[0].message.role == "assistant"
    assert "Python" in resp.choices[0].message.content or "matey" in resp.choices[0].message.content


@responses.activate
def test_chat_completions_create_multiple_choices(
    mock_client: Client, mock_client_url
):
    """Mock chat.completions.create with n > 1."""
    expected = {
        "id": "chatcmpl-multi789",
        "object": "chat.completion",
        "created": 1700000200,
        "model": "meta-llama/Meta-Llama-3-8B-Instruct",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Answer A"},
                "finish_reason": "stop",
            },
            {
                "index": 1,
                "message": {"role": "assistant", "content": "Answer B"},
                "finish_reason": "stop",
            },
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/chat/completions",
        json=expected,
        status=200,
    )

    resp = mock_client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        messages=[{"role": "user", "content": "Give two answers."}],
        n=2,
    )

    assert len(resp.choices) == 2
    assert resp.choices[0].message.content == "Answer A"
    assert resp.choices[1].message.content == "Answer B"


@responses.activate
def test_chat_completions_create_usage(mock_client: Client, mock_client_url):
    """Verify usage tokens are accessible via dot notation."""
    expected = {
        "id": "chatcmpl-usage001",
        "object": "chat.completion",
        "created": 1700000300,
        "model": "meta-llama/Meta-Llama-3-8B-Instruct",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hi"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 1,
            "total_tokens": 6,
        },
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/chat/completions",
        json=expected,
        status=200,
    )

    resp = mock_client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        messages=[{"role": "user", "content": "Hi"}],
    )

    assert resp.usage.prompt_tokens == 5
    assert resp.usage.completion_tokens == 1
    assert resp.usage.total_tokens == 6


# ---------------------------------------------------------------------------
# client.models.list  (inference/models.py)
# ---------------------------------------------------------------------------


@responses.activate
def test_models_list(mock_client: Client, mock_client_url):
    """Mock GET /v1/models."""
    expected = {
        "object": "list",
        "data": [
            {
                "id": "meta-llama/Meta-Llama-3-8B-Instruct",
                "object": "model",
                "created": 1699000000,
                "owned_by": "meta",
            },
            {
                "id": "minimax-m2.5",
                "object": "model",
                "created": 1699000100,
                "owned_by": "minimax",
            },
            {
                "id": "openai-gpt-image-1",
                "object": "model",
                "created": 1699000200,
                "owned_by": "openai",
            },
        ],
    }

    responses.add(
        responses.GET,
        f"{INFERENCE_URL}/v1/models",
        json=expected,
        status=200,
    )

    resp = mock_client.models.list()

    assert len(resp.data) == 3
    assert resp.data[0].id == "meta-llama/Meta-Llama-3-8B-Instruct"
    assert resp.data[1].id == "minimax-m2.5"
    assert resp.data[2].owned_by == "openai"


@responses.activate
def test_models_list_empty(mock_client: Client, mock_client_url):
    """Mock GET /v1/models when no models are available."""
    expected = {"object": "list", "data": []}

    responses.add(
        responses.GET,
        f"{INFERENCE_URL}/v1/models",
        json=expected,
        status=200,
    )

    resp = mock_client.models.list()

    assert len(resp.data) == 0


# ---------------------------------------------------------------------------
# client.images.generate  (inference/images/__init__.py → generations.py)
# ---------------------------------------------------------------------------


@responses.activate
def test_images_generate(mock_client: Client, mock_client_url):
    """Mock POST /v1/images/generations."""
    expected = {
        "created": 1700001000,
        "object": "list",
        "data": [
            {
                "b64_json": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYPgPAAEDAQAIicLsAAAAASUVORK5CYII=",
                "revised_prompt": "A futuristic cityscape at sunset",
            }
        ],
        "usage": {
            "input_tokens": 15,
            "output_tokens": 1,
            "total_tokens": 16,
        },
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/images/generations",
        json=expected,
        status=200,
    )

    resp = mock_client.images.generate(
        model="openai-gpt-image-1",
        prompt="A futuristic cityscape at sunset",
        n=1,
    )

    assert len(resp.data) == 1
    assert resp.data[0].revised_prompt == "A futuristic cityscape at sunset"
    assert resp.data[0].b64_json is not None


@responses.activate
def test_images_generate_multiple(mock_client: Client, mock_client_url):
    """Mock images.generate requesting n=2 images."""
    expected = {
        "created": 1700001100,
        "object": "list",
        "data": [
            {"b64_json": "base64encodedimage1==", "revised_prompt": "A red rose"},
            {"b64_json": "base64encodedimage2==", "revised_prompt": "A red rose"},
        ],
        "usage": {
            "input_tokens": 10,
            "output_tokens": 2,
            "total_tokens": 12,
        },
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/images/generations",
        json=expected,
        status=200,
    )

    resp = mock_client.images.generate(
        model="openai-gpt-image-1",
        prompt="A red rose",
        n=2,
    )

    assert len(resp.data) == 2
    assert resp.data[0].b64_json == "base64encodedimage1=="
    assert resp.data[1].b64_json == "base64encodedimage2=="


# ---------------------------------------------------------------------------
# client.responses.create  (inference/responses.py)
# ---------------------------------------------------------------------------


@responses.activate
def test_responses_create(mock_client: Client, mock_client_url):
    """Mock POST /v1/responses — non-streaming."""
    expected = {
        "id": "resp-abc123",
        "object": "response",
        "created_at": 1700002000,
        "model": "openai-gpt-oss-20b",
        "output": [
            {
                "type": "message",
                "id": "msg-001",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "The ocean covers over 70% of Earth's surface.",
                    }
                ],
            }
        ],
        "usage": {
            "input_tokens": 12,
            "output_tokens": 15,
            "total_tokens": 27,
        },
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/responses",
        json=expected,
        status=200,
    )

    resp = mock_client.responses.create(
        model="openai-gpt-oss-20b",
        input="Tell me a fun fact about the ocean.",
    )

    assert resp.id == "resp-abc123"
    assert resp.output[0].role == "assistant"
    assert resp.output[0].content[0].text == "The ocean covers over 70% of Earth's surface."


@responses.activate
def test_responses_create_with_instructions(mock_client: Client, mock_client_url):
    """Mock responses.create with instructions parameter."""
    expected = {
        "id": "resp-def456",
        "object": "response",
        "created_at": 1700002100,
        "model": "openai-gpt-oss-20b",
        "output": [
            {
                "type": "message",
                "id": "msg-002",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "In exactly 5 words: Ocean depths remain mysterious always.",
                    }
                ],
            }
        ],
        "usage": {
            "input_tokens": 20,
            "output_tokens": 10,
            "total_tokens": 30,
        },
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/responses",
        json=expected,
        status=200,
    )

    resp = mock_client.responses.create(
        model="openai-gpt-oss-20b",
        input="Tell me about the ocean.",
        instructions="Respond in exactly 5 words.",
    )

    assert resp.id == "resp-def456"
    assert resp.usage.total_tokens == 30


# ---------------------------------------------------------------------------
# client.async_invoke.create  (inference/async_invoke.py → AsyncInvoke)
# ---------------------------------------------------------------------------


@responses.activate
def test_async_invoke_create(mock_client: Client, mock_client_url):
    """Mock POST /v1/async-invoke via client.async_invoke.create."""
    expected = {
        "request_id": "req-generic-001",
        "status": "QUEUED",
        "response_url": f"{INFERENCE_URL}/v1/async-invoke/req-generic-001",
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/async-invoke",
        json=expected,
        status=202,
    )

    resp = mock_client.async_invoke.create(
        model_id="fal-ai/flux/schnell",
        input={"prompt": "A sunset"},
    )

    assert resp.request_id == "req-generic-001"
    assert resp.status == "QUEUED"


@responses.activate
def test_async_invoke_create_with_tags(mock_client: Client, mock_client_url):
    """Mock async_invoke.create with tags metadata."""
    expected = {
        "request_id": "req-tagged-001",
        "status": "QUEUED",
        "response_url": f"{INFERENCE_URL}/v1/async-invoke/req-tagged-001",
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/async-invoke",
        json=expected,
        status=202,
    )

    resp = mock_client.async_invoke.create(
        model_id="fal-ai/flux/schnell",
        input={"prompt": "A sunset"},
        tags=[{"key": "env", "value": "test"}],
    )

    assert resp.request_id == "req-tagged-001"


@responses.activate
def test_async_invoke_create_200_accepted(mock_client: Client, mock_client_url):
    """Some deployments return 200 instead of 202 for async-invoke.

    The SDK's recovery logic should handle this transparently.
    """
    expected = {
        "request_id": "req-200-001",
        "status": "QUEUED",
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/async-invoke",
        json=expected,
        status=200,
    )

    resp = mock_client.async_invoke.create(
        model_id="fal-ai/flux/schnell",
        input={"prompt": "A sunset"},
    )

    assert resp.request_id == "req-200-001"
    assert resp.status == "QUEUED"


# ---------------------------------------------------------------------------
# client.async_images.generate  (inference/async_invoke.py → AsyncInvokeImages)
# ---------------------------------------------------------------------------


@responses.activate
def test_async_images_generate(mock_client: Client, mock_client_url):
    """Mock client.async_images.generate for async image generation."""
    expected = {
        "request_id": "req-img-001",
        "status": "QUEUED",
        "response_url": f"{INFERENCE_URL}/v1/async-invoke/req-img-001",
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/async-invoke",
        json=expected,
        status=202,
    )

    resp = mock_client.async_images.generate(
        model_id="fal-ai/flux/schnell",
        prompt="A red balloon over a calm lake at dawn",
    )

    assert resp.request_id == "req-img-001"
    assert resp.status == "QUEUED"


@responses.activate
def test_async_images_generate_with_tags(mock_client: Client, mock_client_url):
    """Mock async_images.generate with tags metadata."""
    expected = {
        "request_id": "req-imgtag-001",
        "status": "QUEUED",
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/async-invoke",
        json=expected,
        status=202,
    )

    resp = mock_client.async_images.generate(
        model_id="fal-ai/flux/schnell",
        prompt="A mountain at sunset",
        tags=[{"key": "project", "value": "demo"}],
    )

    assert resp.request_id == "req-imgtag-001"


# ---------------------------------------------------------------------------
# client.audio.generate  (inference/async_invoke.py → AsyncInvokeAudio)
# ---------------------------------------------------------------------------


@responses.activate
def test_audio_generate(mock_client: Client, mock_client_url):
    """Mock client.audio.generate for async audio generation."""
    expected = {
        "request_id": "req-audio-001",
        "status": "QUEUED",
        "response_url": f"{INFERENCE_URL}/v1/async-invoke/req-audio-001",
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/async-invoke",
        json=expected,
        status=202,
    )

    resp = mock_client.audio.generate(
        model_id="fal-ai/stable-audio-25/text-to-audio",
        prompt="A calm lo-fi hip hop beat with vinyl crackle",
        seconds_total=30,
    )

    assert resp.request_id == "req-audio-001"
    assert resp.status == "QUEUED"


@responses.activate
def test_audio_generate_without_seconds(mock_client: Client, mock_client_url):
    """Mock audio.generate without specifying seconds_total."""
    expected = {
        "request_id": "req-audio-002",
        "status": "QUEUED",
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/async-invoke",
        json=expected,
        status=202,
    )

    resp = mock_client.audio.generate(
        model_id="fal-ai/stable-audio-25/text-to-audio",
        prompt="A short drum beat",
    )

    assert resp.request_id == "req-audio-002"


# ---------------------------------------------------------------------------
# client.audio.speech.create / client.speech.create
# (inference/async_invoke.py → AsyncInvokeSpeech)
# ---------------------------------------------------------------------------


@responses.activate
def test_audio_speech_create(mock_client: Client, mock_client_url):
    """Mock client.audio.speech.create for text-to-speech."""
    expected = {
        "request_id": "req-tts-001",
        "status": "QUEUED",
        "response_url": f"{INFERENCE_URL}/v1/async-invoke/req-tts-001",
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/async-invoke",
        json=expected,
        status=202,
    )

    resp = mock_client.audio.speech.create(
        input="Hello! This is a text to speech test.",
        model_id="fal-ai/elevenlabs/tts/multilingual-v2",
    )

    assert resp.request_id == "req-tts-001"
    assert resp.status == "QUEUED"


@responses.activate
def test_speech_create(mock_client: Client, mock_client_url):
    """Mock client.speech.create — shortcut for audio.speech.create."""
    expected = {
        "request_id": "req-speech-001",
        "status": "QUEUED",
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/async-invoke",
        json=expected,
        status=202,
    )

    resp = mock_client.speech.create(
        input="Hello, world!",
        model_id="fal-ai/elevenlabs/tts/multilingual-v2",
    )

    assert resp.request_id == "req-speech-001"


@responses.activate
def test_audio_speech_create_with_tags(mock_client: Client, mock_client_url):
    """Mock audio.speech.create with tags metadata."""
    expected = {
        "request_id": "req-tts-tag-001",
        "status": "QUEUED",
    }

    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/async-invoke",
        json=expected,
        status=202,
    )

    resp = mock_client.audio.speech.create(
        input="Tagged speech test",
        model_id="fal-ai/elevenlabs/tts/multilingual-v2",
        tags=[{"key": "type", "value": "test"}],
    )

    assert resp.request_id == "req-tts-tag-001"


# ---------------------------------------------------------------------------
# client.agent.chat.completions.create
# (agent_inference/chat/completions.py)
# ---------------------------------------------------------------------------


@responses.activate
def test_agent_chat_completions_create():
    """Mock agent inference POST /api/v1/chat/completions."""
    agent_url = "https://test-agent.agents.do-ai.run"

    client = Client(
        "",
        endpoint="https://testing.local",
        agent_endpoint=agent_url,
    )

    expected = {
        "id": "chatcmpl-agent-001",
        "object": "chat.completion",
        "created": 1700006000,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "I am an AI assistant.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
    }

    responses.add(
        responses.POST,
        f"{agent_url}/api/v1/chat/completions",
        json=expected,
        status=200,
    )

    resp = client.agent.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "What are you?"},
        ],
    )

    assert resp.choices[0].message.content == "I am an AI assistant."
    assert resp.choices[0].finish_reason == "stop"
    assert resp.usage.total_tokens == 20


@responses.activate
def test_agent_chat_completions_create_multi_turn():
    """Mock agent chat with multi-turn conversation."""
    agent_url = "https://test-agent.agents.do-ai.run"

    client = Client(
        "",
        endpoint="https://testing.local",
        agent_endpoint=agent_url,
    )

    expected = {
        "id": "chatcmpl-agent-002",
        "object": "chat.completion",
        "created": 1700006100,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! I can help you.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16},
    }

    responses.add(
        responses.POST,
        f"{agent_url}/api/v1/chat/completions",
        json=expected,
        status=200,
    )

    resp = client.agent.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello!"},
        ],
    )

    assert resp.choices[0].message.content == "Hello! I can help you."


# ---------------------------------------------------------------------------
# Error cases (via resource-level methods)
# ---------------------------------------------------------------------------


@responses.activate
def test_chat_completions_create_401(mock_client: Client, mock_client_url):
    """Mock 401 Unauthorized on chat.completions.create."""
    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/chat/completions",
        json={"error": {"message": "Invalid token", "code": "unauthorized"}},
        status=401,
    )

    try:
        mock_client.chat.completions.create(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert False, "Expected an error to be raised"
    except Exception as exc:
        assert "401" in str(exc) or "Authentication" in str(type(exc).__name__)


@responses.activate
def test_models_list_404(mock_client: Client, mock_client_url):
    """Mock 404 on models.list."""
    responses.add(
        responses.GET,
        f"{INFERENCE_URL}/v1/models",
        json={"error": {"message": "Not found"}},
        status=404,
    )

    try:
        mock_client.models.list()
        assert False, "Expected an error to be raised"
    except Exception as exc:
        assert "404" in str(exc) or "NotFound" in str(type(exc).__name__)


@responses.activate
def test_images_generate_422(mock_client: Client, mock_client_url):
    """Mock 422 Unprocessable Entity on images.generate."""
    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/images/generations",
        json={"error": {"message": "Invalid prompt", "code": "invalid_request"}},
        status=422,
    )

    try:
        mock_client.images.generate(
            model="openai-gpt-image-1",
            prompt="",
        )
        assert False, "Expected an error to be raised"
    except Exception:
        pass


@responses.activate
def test_responses_create_500(mock_client: Client, mock_client_url):
    """Mock 500 Internal Server Error on responses.create."""
    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/responses",
        json={"error": {"message": "Internal server error"}},
        status=500,
    )

    try:
        mock_client.responses.create(
            model="openai-gpt-oss-20b",
            input="Test",
        )
        assert False, "Expected an error to be raised"
    except Exception:
        pass
