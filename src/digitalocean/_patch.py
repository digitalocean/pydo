# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
"""Customize generated code here.

Follow our quickstart for examples: https://aka.ms/azsdk/python/dpcodegen/python/customize
"""
from typing import TYPE_CHECKING

from azure.core.credentials import AccessToken
from azure.core.pipeline.policies import HttpLoggingPolicy

from digitalocean import DigitalOceanClient as DigitalOceanClientGenerated

if TYPE_CHECKING:
    # pylint: disable=unused-import,ungrouped-imports
    from typing import List


class CustomHttpLoggingPolicy(HttpLoggingPolicy):

    # ALLOWED_HEADERS lists headers that will not be redacted when logging
    ALLOWED_HEADERS = set(
        [
            "x-request-id",
            "ratelimit-limit",
            "ratelimit-remaining",
            "ratelimit-reset",
            "x-gateway",
            "x-request-id",
            "x-response-from",
            "CF-Cache-Status",
            "Expect-CT",
            "Server",
            "CF-RAY",
            "Content-Encoding",
        ]
    )

    def __init__(self, logger=None, **kwargs):
        super().__init__(logger, **kwargs)
        self.allowed_header_names.update(self.ALLOWED_HEADERS)


class TokenCredentials:
    """Credential object used for token authentication"""

    def __init__(self, token: str):
        self._token = token
        self._expires_on = 0

    def get_token(self, *args, **kwargs) -> AccessToken:
        return AccessToken(self._token, expires_on=self._expires_on)


class DigitalOceanClient(DigitalOceanClientGenerated):  # type: ignore
    """The official DigitalOceanClient

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


# type: List[str]  # Add all objects you want publicly available to users at this package level
__all__ = ["DigitalOceanClient"]


def patch_sdk():
    """Do not remove from this file.

    `patch_sdk` is a last resort escape hatch that allows you to do customizations
    you can't accomplish using the techniques described in
    https://aka.ms/azsdk/python/dpcodegen/python/customize
    """
