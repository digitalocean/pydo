# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
"""Customize generated code here.

Follow our quickstart for examples: https://aka.ms/azsdk/python/dpcodegen/python/customize
"""
from typing import TYPE_CHECKING, Generator, Any, Dict, Callable

from azure.core.credentials import AccessToken

from pydo.custom_policies import CustomHttpLoggingPolicy
from pydo import GeneratedClient, _version
from pydo.aio import AsyncClient
from pydo import types

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

    :param token: A valid API token.
    :type token: str
    :keyword endpoint: Service URL. Default value is "https://api.digitalocean.com".
    :paramtype endpoint: str
    """

    def paginate(self, method: Callable[..., Dict[str, Any]], *args, **kwargs) -> Generator[Dict[str, Any], None, None]:
        """Automatically paginate through all results from a method that returns paginated data.

        :param method: The method to call (e.g., self.droplets.list)
        :param args: Positional arguments to pass to the method
        :param kwargs: Keyword arguments to pass to the method
        :return: Generator yielding all items from all pages
        :rtype: Generator[Dict[str, Any], None, None]
        """
        page = 1
        per_page = kwargs.get('per_page', 20)  # Default per_page if not specified

        while True:
            # Set the current page
            kwargs['page'] = page
            kwargs['per_page'] = per_page

            # Call the method
            result = method(*args, **kwargs)

            # Yield items from this page
            items_key = None
            if hasattr(result, 'keys') and callable(getattr(result, 'keys')):
                # Find the key that contains the list of items
                for key in result.keys():
                    if key.endswith('s') and isinstance(result[key], list):  # e.g., 'droplets', 'ssh_keys'
                        items_key = key
                        break

            if items_key and items_key in result:
                yield from result[items_key]
            else:
                # If we can't find the items key, yield the whole result once
                yield result
                break

            # Check if there's a next page
            links = result.get('links', {})
            pages = links.get('pages', {})
            if 'next' not in pages:
                break

            page += 1
        logger = kwargs.get("logger")
        if logger is not None and kwargs.get("http_logging_policy") == "":
            kwargs["http_logging_policy"] = CustomHttpLoggingPolicy(logger=logger)
        sdk_moniker = f"pydo/{_version.VERSION}"

        super().__init__(
            TokenCredentials(token), timeout=timeout, sdk_moniker=sdk_moniker, **kwargs
        )


__all__ = ["Client", "AsyncClient", "types"]


def patch_sdk():
    """Do not remove from this file.

    `patch_sdk` is a last resort escape hatch that allows you to do customizations
    you can't accomplish using the techniques described in
    https://aka.ms/azsdk/python/dpcodegen/python/customize
    """
