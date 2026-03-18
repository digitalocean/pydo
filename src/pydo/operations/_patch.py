# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
"""Customize generated code here.

Follow our quickstart for examples: https://aka.ms/azsdk/python/dpcodegen/python/customize

Streaming for inference / agent-inference operations
-----------------------------------------------------
All generated methods on ``InferenceOperations`` and
``AgentInferenceOperations`` that accept a ``body`` parameter are
**automatically** wrapped at init time.  When the caller passes
``"stream": True`` in the request body, the wrapper bypasses the
generated (non-streaming) code, runs the HTTP pipeline with
``stream=True``, and returns an :class:`~pydo.custom_extensions.SSEStream`.

This means new endpoints added to the OpenAPI spec and regenerated via
``make generate`` get streaming support with **zero manual changes** to
this file.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # pylint: disable=unused-import,ungrouped-imports
    pass

# ---------------------------------------------------------------------------
# Serverless Inference operations
# ---------------------------------------------------------------------------

try:
    from ._operations import InferenceOperations as _GeneratedInferenceOperations

    import pydo.operations._operations as _ops

    _HAS_INFERENCE = True
except ImportError:
    _HAS_INFERENCE = False

if _HAS_INFERENCE:
    from pydo.custom_extensions import (
        StreamingMixin,
        install_streaming_wrappers,
    )

    class InferenceOperations(StreamingMixin, _GeneratedInferenceOperations):
        """InferenceOperations with fully automatic streaming support.

        Every generated method that takes a ``body`` parameter is wrapped
        so that ``body["stream"] == True`` triggers SSE streaming
        automatically.  No per-endpoint overrides are needed.
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            install_streaming_wrappers(
                self, _GeneratedInferenceOperations, _ops, is_async=False
            )


# ---------------------------------------------------------------------------
# Agent Inference operations
# ---------------------------------------------------------------------------

try:
    from ._operations import (
        AgentInferenceOperations as _GeneratedAgentInferenceOperations,
    )

    if not _HAS_INFERENCE:
        import pydo.operations._operations as _ops

    _HAS_AGENT_INFERENCE = True
except ImportError:
    _HAS_AGENT_INFERENCE = False

if _HAS_AGENT_INFERENCE:
    if not _HAS_INFERENCE:
        from pydo.custom_extensions import (
            StreamingMixin,
            install_streaming_wrappers,
        )

    class AgentInferenceOperations(StreamingMixin, _GeneratedAgentInferenceOperations):
        """AgentInferenceOperations with fully automatic streaming support.

        Same auto-wrapping strategy as ``InferenceOperations``.  The
        builder prefix is derived from the class name
        (``agent_inference``), so builders named
        ``build_agent_inference_<method>_request`` are discovered
        automatically.
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            install_streaming_wrappers(
                self, _GeneratedAgentInferenceOperations, _ops, is_async=False
            )


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = []  # type: ignore[assignment]
if _HAS_INFERENCE:
    __all__.append("InferenceOperations")
if _HAS_AGENT_INFERENCE:
    __all__.append("AgentInferenceOperations")


def patch_sdk():
    """Do not remove from this file.

    `patch_sdk` is a last resort escape hatch that allows you to do customizations
    you can't accomplish using the techniques described in
    https://aka.ms/azsdk/python/dpcodegen/python/customize
    """
