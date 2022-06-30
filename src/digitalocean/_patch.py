# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
"""Customize generated code here.

Follow our quickstart for examples: https://aka.ms/azsdk/python/dpcodegen/python/customize
"""
from typing import TYPE_CHECKING

from azure.core.credentials import AccessToken

from digitalocean import DigitalOceanClient as DigitalOceanClientGenerated

if TYPE_CHECKING:
    # pylint: disable=unused-import,ungrouped-imports
    from typing import List


def get_version():
    # TODO: Read version from version.txt once it's created by CI
    return "dev"


class TokenCredentials:
    """DO Customized Code:
    Added to simply authentication.
    """

    def __init__(self, token: str):
        self._token = token
        self._expires_on = 0

    def get_token(self, *args, **kwargs) -> AccessToken:
        return AccessToken(self._token, expires_on=self._expires_on)


class DigitalOceanClient(DigitalOceanClientGenerated):
    """DO Customized Code:
    This client patch adds the TokenCredentials to the DO client init.
    """

    def __init__(self, token: str, **kwargs):
        kwargs["user_agent"] = f"digitalocean/{get_version}"

        super().__init__(credential=TokenCredentials(token), **kwargs)


# type: List[str]  # Add all objects you want publicly available to users at this package level
__all__ = ["DigitalOceanClient"]


def patch_sdk():
    """Do not remove from this file.

    `patch_sdk` is a last resort escape hatch that allows you to do customizations
    you can't accomplish using the techniques described in
    https://aka.ms/azsdk/python/dpcodegen/python/customize
    """
