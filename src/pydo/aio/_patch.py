# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
"""Customize generated code here.

Follow our quickstart for examples: https://aka.ms/azsdk/python/dpcodegen/python/customize
"""
from typing import TYPE_CHECKING, Optional

from azure.core.credentials import AccessToken
from azure.core.credentials_async import AsyncTokenCredential

from pydo import _version
from pydo.custom_policies import CustomHttpLoggingPolicy
from pydo.custom_extensions import _BaseURLProxy, INFERENCE_BASE_URL
from pydo.aio import GeneratedClient

if TYPE_CHECKING:
    # pylint: disable=unused-import,ungrouped-imports
    from typing import List

try:
    from pydo.resources.client_surface import AgentClientSurface, InferenceClientSurface
except ImportError:  # pragma: no cover

    class InferenceClientSurface:  # type: ignore[too-few-public-methods]
        """Placeholder when ``resources/client_surface.py`` is missing."""

    class AgentClientSurface:  # type: ignore[too-few-public-methods]
        """Placeholder when ``resources/client_surface.py`` is missing."""


class TokenCredentials(AsyncTokenCredential):
    """DO Customized Code:
    Added to simplify authentication.
    """

    def __init__(self, token: str):
        self._token = token
        self._expires_on = 0

    async def get_token(self, *args, **kwargs) -> AccessToken:
        return AccessToken(self._token, expires_on=self._expires_on)


class Client(  # type: ignore
    InferenceClientSurface,
    AgentClientSurface,
    GeneratedClient,
):
    """The official DigitalOcean Python client (async)

    :param token: A valid API token / model access key (positional or ``token=``).
    :type token: str
    :keyword api_key: Same as ``token`` — OpenAI-style alias for a model access key.
    :paramtype api_key: str
    :keyword endpoint: Service URL. Default value is "https://api.digitalocean.com".
    :paramtype endpoint: str
    :keyword inference_endpoint: Serverless inference URL.
        Default value is "https://inference.do-ai.run".
    :paramtype inference_endpoint: str
    :keyword agent_endpoint: Agent inference URL.  Pass the per-agent
        subdomain (e.g. ``"https://<id>.agents.do-ai.run"``).
        Required only when using agent inference endpoints.
    :paramtype agent_endpoint: str
    """

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        api_key: Optional[str] = None,
        timeout: int = 120,
        inference_endpoint: str = INFERENCE_BASE_URL,
        agent_endpoint: str = "",
        **kwargs,
    ):
        if token is not None and api_key is not None:
            raise TypeError("Pass only one of token or api_key.")
        resolved: Optional[str] = token if token is not None else api_key
        if not resolved:
            raise TypeError(
                "Client() requires a token or api_key "
                "(e.g. Client(os.environ['MODEL_ACCESS_KEY']) or Client(api_key=...))."
            )

        logger = kwargs.get("logger")
        if logger is not None and kwargs.get("http_logging_policy") == "":
            kwargs["http_logging_policy"] = CustomHttpLoggingPolicy(logger=logger)
        sdk_moniker = f"pydo/{_version.VERSION}"

        super().__init__(
            TokenCredentials(resolved), timeout=timeout, sdk_moniker=sdk_moniker, **kwargs
        )

        self._setup_inference_routing(inference_endpoint, agent_endpoint)

        self._inference_resource_root = None
        self._agent_inference_resource_root = None
        try:
            from pydo.resources.aio.agent_inference import AgentInferenceResources
            from pydo.resources.aio.inference import InferenceResources
        except ImportError:
            pass
        else:
            self._inference_resource_root = InferenceResources(self)
            self._agent_inference_resource_root = AgentInferenceResources(self)

        # Inject inference methods onto the existing DO v2 images object
        # so client.images.create_custom() (DO v2) and client.images.generate() (inference)
        # both work on the same object — fully backward compatible.
        if "images" in self.__dict__ and self._inference_resource_root is not None:
            inference_images = self._inference_resource_root.images
            self.images.generate = inference_images.generate
            self.images.generations = inference_images.generations

    def _setup_inference_routing(
        self,
        inference_endpoint: str,
        agent_endpoint: str,
    ) -> None:
        """Route Inference / AgentInference operation groups to their endpoints.

        * ``*Inference*`` (but not ``*AgentInference*``) → *inference_endpoint*
        * ``*AgentInference*`` → *agent_endpoint*

        Both use the same token passed to ``Client.__init__``.
        """
        inference_proxy = _BaseURLProxy(
            self._client,
            inference_endpoint,
        )

        agent_proxy = None
        if agent_endpoint:
            agent_proxy = _BaseURLProxy(
                self._client,
                agent_endpoint,
            )

        for attr in self.__dict__.values():
            if not hasattr(attr, "_client"):
                continue
            class_name = type(attr).__name__
            if class_name.startswith("AgentInference") and agent_proxy:
                attr._client = agent_proxy
            elif class_name.startswith("Inference"):
                attr._client = inference_proxy

    def _require_inference_resource_root(self):
        if self._inference_resource_root is None:
            raise RuntimeError(
                "Async inference resource packages are missing; run ``make generate`` "
                "(they are produced by ``scripts/generate_inference_resources.py``)."
            )
        return self._inference_resource_root

    def _require_agent_inference_resource_root(self):
        if self._agent_inference_resource_root is None:
            raise RuntimeError(
                "Async agent inference resource packages are missing; run ``make generate`` "
                "(they are produced by ``scripts/generate_inference_resources.py``)."
            )
        return self._agent_inference_resource_root


# Add all objects you want publicly available to users at this package level
__all__ = ["Client"]  # type: List[str]


def patch_sdk():
    """Do not remove from this file.

    `patch_sdk` is a last resort escape hatch that allows you to do customizations
    you can't accomplish using the techniques described in
    https://aka.ms/azsdk/python/dpcodegen/python/customize
    """
