""" Custom client exceptions"""

from azure.core.exceptions import HttpResponseError as AzCoreHttpResponseError
from pydantic import ValidationError

from digitalocean import models


class DigitaloceanAPIError(Exception):
    """Raised when the API responds with an error due to a non-success status"""

    def __init__(self, api_error: models.Error, *args: object) -> None:
        super().__init__(f"{api_error.id}: {api_error.message}", *args)


class ResponseDeserializationError(Exception):
    """Raised when the client is unable to deserialize the response into an
    appropriate model
    """


class HttpResponseError(AzCoreHttpResponseError):
    """Raised when an error that occurs during the HTTP request pipeline."""


class ModelValidationError(ValidationError):
    """Raised when model initization fails due to model validation errors."""
