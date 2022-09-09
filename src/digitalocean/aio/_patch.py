# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
"""Customize generated code here.

Follow our quickstart for examples: https://aka.ms/azsdk/python/dpcodegen/python/customize
"""
from typing import TYPE_CHECKING

from azure.core.credentials import AccessToken

from digitalocean.custom_policies import CustomHttpLoggingPolicy
from digitalocean.aio import GeneratedClient

if TYPE_CHECKING:
    # pylint: disable=unused-import,ungrouped-imports
    from typing import List


class TokenCredentials:
    """DO Customized Code:
    Added to simplify authentication.
    """

    def __init__(self, token: str):
        self._token = token
        self._expires_on = 0

    async def get_token(self, *args, **kwargs) -> AccessToken:
        return AccessToken(self._token, expires_on=self._expires_on)


class Client(GeneratedClient):  # type: ignore
    """The official DigitalOcean Python client

    :param token: A valid API token.
    :type token: str
    :keyword endpoint: Service URL. Default value is "https://api.digitalocean.com".
    :paramtype endpoint: str
    """

    def __init__(self, token: str, *, timeout: int = 120, **kwargs):
        logger = kwargs.get("logger")
        if logger is not None and kwargs.get("http_logging_policy") == "":
            kwargs["http_logging_policy"] = CustomHttpLoggingPolicy(logger=logger)
        super().__init__(TokenCredentials(token), timeout=timeout, **kwargs)


# Add all objects you want publicly available to users at this package level
__all__ = ["Client"]  # type: List[str]


def patch_sdk():
    """Do not remove from this file.

    `patch_sdk` is a last resort escape hatch that allows you to do customizations
    you can't accomplish using the techniques described in
    https://aka.ms/azsdk/python/dpcodegen/python/customize
    """
