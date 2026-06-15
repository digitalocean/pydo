# pylint: disable=line-too-long
"""Mock tests for the ``pydo.inference`` namespace entry point.

These tests exercise the same inference endpoints as ``test_inference.py``
but through ``from pydo.inference import Client`` to confirm the
namespaced client is a fully integrated drop-in for the core
:class:`pydo.Client`.
"""

import responses

import pydo
import pydo.inference
from pydo.inference import Client as InferenceClient


INFERENCE_URL = "https://inference.do-ai.run"


# ---------------------------------------------------------------------------
# Module shape
# ---------------------------------------------------------------------------


def test_namespace_module_exports():
    """``pydo.inference`` exposes ``Client`` and ``TokenCredentials``."""
    assert hasattr(pydo.inference, "Client")
    assert hasattr(pydo.inference, "TokenCredentials")
    assert "Client" in pydo.inference.__all__
    assert "TokenCredentials" in pydo.inference.__all__


def test_namespace_client_is_subclass_of_core_client():
    """The namespaced client inherits the core ``pydo.Client`` machinery."""
    assert issubclass(InferenceClient, pydo.Client)


def test_namespace_client_dir_is_inference_focused():
    """``dir(client)`` advertises inference / agent namespaces only.

    The list is auto-discovered from the OpenAPI spec, so adding new
    inference endpoints surfaces them here automatically.
    """
    client = InferenceClient(token="dummy")
    surface = set(dir(client))

    # Core inference primitives every inference SDK is expected to expose.
    expected_minimum = {
        "chat",
        "models",
        "embeddings",
        "images",
        "responses",
        "batches",
        "async_invoke",
        "audio",
        "speech",
        "agent",
    }
    missing = expected_minimum - surface
    assert not missing, f"missing inference namespaces: {missing}"

    # v2 cloud surfaces are intentionally hidden from ``dir()`` even though
    # they still resolve via inheritance — keeps editor autocomplete focused.
    for v2_attr in ("droplets", "kubernetes", "domains", "load_balancers"):
        assert v2_attr not in surface


def test_namespace_client_repr_is_distinct():
    client = InferenceClient(token="dummy")
    assert repr(client) == "<pydo.inference.Client>"


def test_namespace_client_token_or_api_key_required():
    """Constructor mirrors the core client's auth ergonomics."""
    import pytest

    with pytest.raises(TypeError):
        InferenceClient()  # neither token nor api_key

    with pytest.raises(TypeError):
        InferenceClient("tok", api_key="key")  # both supplied

    # Either keyword works.
    assert InferenceClient(token="t") is not None
    assert InferenceClient(api_key="k") is not None


# ---------------------------------------------------------------------------
# End-to-end smoke (chat / models / images / agent) via the namespaced client
# ---------------------------------------------------------------------------


@responses.activate
def test_namespace_chat_completions_create():
    """``client.chat.completions.create`` routes to the inference URL."""
    client = InferenceClient(token="dummy", endpoint="https://testing.local")
    expected = {
        "id": "chatcmpl-ns001",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "llama3.3-70b-instruct",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hi from namespace"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 3,
            "completion_tokens": 4,
            "total_tokens": 7,
        },
    }
    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/chat/completions",
        json=expected,
        status=200,
    )

    resp = client.chat.completions.create(
        model="llama3.3-70b-instruct",
        messages=[{"role": "user", "content": "Hello!"}],
    )

    assert resp.id == "chatcmpl-ns001"
    assert resp.choices[0].message.content == "Hi from namespace"


@responses.activate
def test_namespace_models_list():
    client = InferenceClient(token="dummy", endpoint="https://testing.local")
    expected = {
        "object": "list",
        "data": [
            {
                "id": "llama3.3-70b-instruct",
                "object": "model",
                "created": 1,
                "owned_by": "meta",
            },
        ],
    }
    responses.add(
        responses.GET,
        f"{INFERENCE_URL}/v1/models",
        json=expected,
        status=200,
    )

    resp = client.models.list()
    assert resp.data[0].id == "llama3.3-70b-instruct"


@responses.activate
def test_namespace_images_generate():
    """``client.images.generate`` exists on the namespaced client via the
    same ``ImagesOperations`` injection used by the core client."""
    client = InferenceClient(token="dummy", endpoint="https://testing.local")
    expected = {
        "created": 1700000000,
        "object": "list",
        "data": [{"b64_json": "abc==", "revised_prompt": "A sunset"}],
        "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
    }
    responses.add(
        responses.POST,
        f"{INFERENCE_URL}/v1/images/generations",
        json=expected,
        status=200,
    )

    resp = client.images.generate(model="openai-gpt-image-1", prompt="A sunset", n=1)
    assert resp.data[0].b64_json == "abc=="


@responses.activate
def test_namespace_agent_chat_completions_create():
    """Agent inference also works via the namespaced client."""
    agent_url = "https://ns-agent.agents.do-ai.run"
    client = InferenceClient(
        token="dummy",
        endpoint="https://testing.local",
        agent_endpoint=agent_url,
    )
    expected = {
        "id": "chatcmpl-agent-ns001",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "agent reply"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
    }
    responses.add(
        responses.POST,
        f"{agent_url}/api/v1/chat/completions",
        json=expected,
        status=200,
    )

    resp = client.agent.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hi"}],
    )
    assert resp.choices[0].message.content == "agent reply"


# ---------------------------------------------------------------------------
# Async namespace client
# ---------------------------------------------------------------------------


def test_async_namespace_module_exports():
    """``pydo.inference.aio`` mirrors the sync namespace."""
    import pydo.inference.aio as aio_ns
    import pydo.aio

    assert hasattr(aio_ns, "Client")
    assert hasattr(aio_ns, "TokenCredentials")
    assert issubclass(aio_ns.Client, pydo.aio.Client)


def test_async_namespace_client_dir_and_repr():
    from pydo.inference.aio import Client as AsyncInferenceClient

    client = AsyncInferenceClient(token="dummy")
    assert repr(client) == "<pydo.inference.aio.Client>"
    surface = set(dir(client))
    for name in ("chat", "models", "embeddings", "images", "responses", "agent"):
        assert name in surface
