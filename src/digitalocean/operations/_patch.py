# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
"""Customize generated code here.

Follow our quickstart for examples: 
https://aka.ms/azsdk/python/dpcodegen/python/customize
"""
from typing import Any, List, Tuple, Union

from azure.core.exceptions import HttpResponseError as AzHttpResponseError
from pydantic import DictError, ValidationError, parse_obj_as

from digitalocean import custom_errors, models
from ._operations import (
    AccountOperations as AccountOperationsGenerated,
    DropletsOperations as DropletsOperationsGenerated,
)


class AccountOperations(AccountOperationsGenerated):
    """Operations to interact with Account API resource"""

    def get(self, *args, **kwargs: Any) -> models.Account:
        """Get Account User Information.

        :return: Account
        :rtype: ~digitalocean.models.Account
        :raises ~digitalocean.custom_errors.HttpResponseError: when an HTTP error
            occurs
        :raises ~digitalocean.custom_errors.DigitaloceanAPIError: when the API returns
            an error response
        :raises ~digitalocean.custom_errors.ResponseDeserializationError: when the
            response data could not be parsed into an Account instance
        """
        try:
            get_resp = super().get(*args, **kwargs)
        except AzHttpResponseError as az_err:
            raise custom_errors.HttpResponseError(
                az_err.message, az_err.response
            ) from az_err

        try:
            account_dict = get_resp["account"]
            return models.Account(**account_dict)
        except KeyError as exc:
            try:
                err = models.Error.validate(get_resp)
                if err is not None:
                    raise custom_errors.DigitaloceanAPIError(api_error=err) from exc
            except DictError as err_exc:
                raise custom_errors.ResponseDeserializationError(
                    "unable to serialize account get error response"
                ) from err_exc

        raise custom_errors.ResponseDeserializationError(
            "unable to serialize account get response"
        )


class DropletsOperations(DropletsOperationsGenerated):
    """Operations to interact with Droplets API resource"""

    def list(self, *args, **kwargs: Any) -> List[models.Droplet]:
        """List droplets

        :return: List[Droplet]
        :rtype: List[~digitalocean.models.Droplet]
        :raises ~digitalocean.custom_errors.HttpResponseError: when an HTTP error
            occurs
        :raises ~digitalocean.custom_errors.DigitaloceanAPIError: when the API returns
            an error response
        :raises ~digitalocean.custom_errors.ResponseDeserializationError: when the
            response data could not be parsed into a list of Droplet instances
        """
        try:
            list_resp = super().list(*args, **kwargs)
        except AzHttpResponseError as az_err:
            raise custom_errors.HttpResponseError(
                az_err.message, az_err.response
            ) from az_err

        try:
            droplets_list = list_resp["droplets"]
            return parse_obj_as(List[models.Droplet], droplets_list)
        except KeyError as exc:
            try:
                err = models.Error.validate(list_resp)
                if err is not None:
                    raise custom_errors.DigitaloceanAPIError(api_error=err) from exc
            except DictError as err_exc:
                raise custom_errors.ResponseDeserializationError(
                    "unable to serialize droplets list error response"
                ) from err_exc
        except ValidationError as exc:
            raise custom_errors.ModelValidationError(exc.raw_errors, exc.model) from exc

        raise custom_errors.ResponseDeserializationError(
            "unable to serialize droplets list response"
        )

    def create(  # pylint: disable=arguments-renamed
        self,
        droplet_create: Union[models.DropletSingleCreate, models.DropletMultiCreate],
        **kwargs: Any
    ) -> Tuple[models.Droplet, dict]:
        """Create a new droplet

        :param droplet_create: The details of the create droplet request
        :type droplet_create: ~digitalocean.models.DropletSingleCreate or
            ~digitalocean.models.DropletMultiCreate
        :return: Droplet
        :rtype: ~digitalocean.models.Droplet
        :raises ~digitalocean.custom_errors.HttpResponseError: when an HTTP error
            occurs
        :raises ~digitalocean.custom_errors.DigitaloceanAPIError: when the API returns
            an error response
        :raises ~digitalocean.custom_errors.ResponseDeserializationError: when the
            response data could not be parsed into a Droplet instance
        """
        try:
            create_req = droplet_create.dict(exclude_unset=True)
            create_resp = super().create(create_req, **kwargs)
        except AzHttpResponseError as az_err:
            raise custom_errors.HttpResponseError(
                az_err.message, az_err.response
            ) from az_err

        try:
            droplet_data = create_resp["droplet"]
            links_data = create_resp["links"]
            droplet = parse_obj_as(models.Droplet, droplet_data)
            return droplet, links_data
        except KeyError as exc:
            try:
                err = models.Error.validate(create_resp)
                if err is not None:
                    raise custom_errors.DigitaloceanAPIError(api_error=err) from exc
            except ValidationError as err_exc:
                raise custom_errors.ResponseDeserializationError(
                    "unable to serialize droplets create error response"
                ) from err_exc
        except ValidationError as exc:
            raise custom_errors.ModelValidationError(exc.raw_errors, exc.model) from exc

        raise custom_errors.ResponseDeserializationError(
            "unable to serialize droplet create response"
        )


__all__ = [
    "AccountOperations",
    "DropletsOperations",
]  # Add all objects you want publicly available to users at this package level


def patch_sdk():
    """Do not remove from this file.

    `patch_sdk` is a last resort escape hatch that allows you to do customizations
    you can't accomplish using the techniques described in
    https://aka.ms/azsdk/python/dpcodegen/python/customize
    """
