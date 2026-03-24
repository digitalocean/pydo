# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
"""Customize generated code here.

Follow our quickstart for examples: https://aka.ms/azsdk/python/dpcodegen/python/customize

Async mirror of ``pydo/operations/_patch.py``.  See that module for the
full design rationale.  If no inference / agent-inference operations have
been generated, this module exports nothing.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # pylint: disable=unused-import,ungrouped-imports
    from typing import List

# ---------------------------------------------------------------------------
# Serverless Inference operations (async)
# ---------------------------------------------------------------------------

try:
    from ._operations import InferenceOperations as _GeneratedInferenceOperations

    import pydo.operations._operations as _ops

    _HAS_INFERENCE = True
except ImportError:
    _HAS_INFERENCE = False

if _HAS_INFERENCE:
    from pydo.custom_extensions import (
        AsyncStreamingMixin,
        install_streaming_wrappers,
    )

    class InferenceOperations(AsyncStreamingMixin, _GeneratedInferenceOperations):
        """Async InferenceOperations with fully automatic streaming support.

        Mirror of the sync version in ``pydo/operations/_patch.py``.
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            install_streaming_wrappers(
                self, _GeneratedInferenceOperations, _ops, is_async=True
            )


# ---------------------------------------------------------------------------
# Agent Inference operations (async)
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
            AsyncStreamingMixin,
            install_streaming_wrappers,
        )

    class AgentInferenceOperations(
        AsyncStreamingMixin, _GeneratedAgentInferenceOperations
    ):
        """Async AgentInferenceOperations with fully automatic streaming support.

        Mirror of the sync version in ``pydo/operations/_patch.py``.
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            install_streaming_wrappers(
                self, _GeneratedAgentInferenceOperations, _ops, is_async=True
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
