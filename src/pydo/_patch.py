# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
"""Customize generated code here.

Follow our quickstart for examples: https://aka.ms/azsdk/python/dpcodegen/python/customize
"""
from typing import TYPE_CHECKING, Generator, Any, Dict, Callable, Optional, Union

from azure.core.credentials import AccessToken
from azure.core.exceptions import HttpResponseError
from azure.core.pipeline.policies import RetryPolicy

from pydo.custom_policies import CustomHttpLoggingPolicy
from pydo import GeneratedClient, _version
from pydo.aio import AsyncClient
from pydo import types
from pydo import exceptions

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
    :keyword retry_total: Total number of retries for failed requests. Default is 3.
    :paramtype retry_total: int
    :keyword retry_backoff_factor: Backoff factor for retry delays. Default is 0.5.
    :paramtype retry_backoff_factor: float
    :keyword retry_status_codes: HTTP status codes to retry on. Default is [429, 500, 502, 503, 504].
    :paramtype retry_status_codes: list[int]
    :keyword timeout: Request timeout in seconds. Default is 120.
    :paramtype timeout: int
    """

    def __init__(
        self,
        token: str,
        *,
        retry_total: int = 3,
        retry_backoff_factor: float = 0.5,
        retry_status_codes: Optional[list[int]] = None,
        timeout: int = 120,
        **kwargs
    ):
        # Set default retry status codes if not provided
        if retry_status_codes is None:
            retry_status_codes = [429, 500, 502, 503, 504]

        # Create custom retry policy with user-specified parameters
        retry_policy = RetryPolicy(
            retry_total=retry_total,
            retry_backoff_factor=retry_backoff_factor,
            retry_on_status_codes=retry_status_codes,
        )

        # Add retry policy to kwargs if not already specified
        if 'retry_policy' not in kwargs:
            kwargs['retry_policy'] = retry_policy

        # Handle logging policy
        logger = kwargs.get("logger")
        if logger is not None and kwargs.get("http_logging_policy") == "":
            kwargs["http_logging_policy"] = CustomHttpLoggingPolicy(logger=logger)
        sdk_moniker = f"pydo/{_version.VERSION}"

        super().__init__(
            TokenCredentials(token), timeout=timeout, sdk_moniker=sdk_moniker, **kwargs
        )

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

    @staticmethod
    def _handle_http_error(error: HttpResponseError) -> exceptions.DigitalOceanError:
        """Convert HTTP errors to appropriate DigitalOcean custom exceptions.

        :param error: The HttpResponseError from azure
        :return: Appropriate DigitalOcean exception
        :rtype: exceptions.DigitalOceanError
        """
        status_code = getattr(error, 'status', None) or getattr(error.response, 'status_code', None)

        if status_code == 401:
            return exceptions.AuthenticationError(
                "Authentication failed. Please check your API token.",
                status_code=status_code,
                response=error.response
            )
        elif status_code == 403:
            return exceptions.PermissionDeniedError(
                "Access forbidden. You don't have permission to perform this action.",
                status_code=status_code,
                response=error.response
            )
        elif status_code == 404:
            return exceptions.ResourceNotFoundError(
                "Resource not found. The requested resource does not exist.",
                status_code=status_code,
                response=error.response
            )
        elif status_code == 400:
            return exceptions.ValidationError(
                "Bad request. Please check your request parameters.",
                status_code=status_code,
                response=error.response
            )
        elif status_code == 409:
            return exceptions.ConflictError(
                "Conflict. The resource is in a state that conflicts with the request.",
                status_code=status_code,
                response=error.response
            )
        elif status_code == 429:
            return exceptions.RateLimitError(
                "Rate limit exceeded. Please wait before making more requests.",
                status_code=status_code,
                response=error.response
            )
        elif status_code and status_code >= 500:
            return exceptions.ServerError(
                "Server error. Please try again later.",
                status_code=status_code,
                response=error.response
            )
        elif status_code == 503:
            return exceptions.ServiceUnavailableError(
                "Service temporarily unavailable. Please try again later.",
                status_code=status_code,
                response=error.response
            )
        else:
            # Fallback to generic DigitalOcean error
            return exceptions.DigitalOceanError(
                f"API request failed: {str(error)}",
                status_code=status_code,
                response=error.response
            )


__all__ = ["Client", "AsyncClient", "types", "exceptions"]


def patch_sdk():
    """Do not remove from this file.

    `patch_sdk` is a last resort escape hatch that allows you to do customizations
    you can't accomplish using the techniques described in
    https://aka.ms/azsdk/python/dpcodegen/python/customize
    """
