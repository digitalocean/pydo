# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
"""Customize generated code here.

Follow our quickstart for examples: https://aka.ms/azsdk/python/dpcodegen/python/customize
"""
from typing import TYPE_CHECKING

from azure.core.credentials import AccessToken

from pydo.custom_policies import CustomHttpLoggingPolicy
from pydo.custom_extensions import _BaseURLProxy, INFERENCE_BASE_URL
from pydo import GeneratedClient, _version

if TYPE_CHECKING:
    # pylint: disable=unused-import,ungrouped-imports
    from typing import List


class TokenCredentials:
    """Credential object used for token authentication"""

    def __init__(self, token: str):
        self._token = token
        self._expires_on = 0

    def get_token(self, *args, **kwargs) -> AccessToken:
        return AccessToken(self._token, expires_on=self._expires_on)


class Client(GeneratedClient):  # type: ignore
    """The official DigitalOcean Python client

    :param token: A valid API token / model access key.
    :type token: str
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
        token: str,
        *,
        timeout: int = 120,
        inference_endpoint: str = INFERENCE_BASE_URL,
        agent_endpoint: str = "",
        **kwargs,
    ):
        logger = kwargs.get("logger")
        if logger is not None and kwargs.get("http_logging_policy") == "":
            kwargs["http_logging_policy"] = CustomHttpLoggingPolicy(logger=logger)
        sdk_moniker = f"pydo/{_version.VERSION}"

        super().__init__(
            TokenCredentials(token), timeout=timeout, sdk_moniker=sdk_moniker, **kwargs
        )

        self._setup_inference_routing(inference_endpoint, agent_endpoint)

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


__all__ = ["Client"]


def patch_sdk():
    """Do not remove from this file.

    `patch_sdk` is a last resort escape hatch that allows you to do customizations
    you can't accomplish using the techniques described in
    https://aka.ms/azsdk/python/dpcodegen/python/customize
    """
