from typing import Tuple, Union

import azure.core.exceptions as azure_exceptions
from generated.digitalocean import DigitalOceanClient
from generated.digitalocean.models import (
    Action,
    Droplet,
    DropletActionRename,
    DropletSingleCreate,
    Error,
    SingleDropletResponse,
    Components1Fz6HvkResponsesExistingDropletContentApplicationJsonSchema as DropletResponse,
    Components1Sllx9CResponsesDropletActionContentApplicationJsonSchema as DropletActionResponse
)
from msrest.serialization import Model as BaseModel

from digitalocean import exceptions
from digitalocean.api import TokenCredential


def _validate(obj: BaseModel):
    if not isinstance(obj, BaseModel):
        raise exceptions.InvalidModelException(value=obj)
    validation_errors = obj.validate()
    if len(validation_errors) > 0:
        raise exceptions.ModelValidationException(errors=validation_errors)


def _handle_error(response) -> Union[Error, None]:
    if type(response) is dict:
        if response.get("message") != "":
            return Error.from_dict(response)
    
    if type(response) is Error:
        return response


class DropletsAPI:
    """Provides methods to interact with the DigitalOcean Droplet API Endpoint

    Attributes:
        api_token: A valid DigitalOcean API token
    """

    def __init__(self, api_token: str, droplet_id: int = 0):
        self._credential = TokenCredential(api_token, 0)

    def _client(self, droplet_id: int = 0):
        return DigitalOceanClient(credential=self._credential, droplet_id=droplet_id)

    def create_single(self, request: DropletSingleCreate) -> Tuple[Droplet, int]:
        """Creates a single droplet.

        Args:
            request (DropletSingleCreate): An instance of DropletSingleCreate with the respective propertis set to
            create a new droplet.

        Raises:
            exceptions.BaseHTTPException: For HTTP transport level errors raised by the generated client.
            exceptions.APIError: For errors with the Request.
            exceptions.Unprocessable: In the event the the response could not be processed and no known error was
            handled.

        Returns:
            Tuple[Droplet, int]: If succesful, retuns a Droplet and the ActionID of the create droplet action.
        """

        _validate(request)

        api = self._client()
        try:
            res = api.create.droplet(body=request)
        except azure_exceptions.HttpResponseError as e:
            raise exceptions.BaseHTTPException(str(e))

        if type(res) is dict:
            if res.get("droplet") is not None:
                droplet_response: SingleDropletResponse = SingleDropletResponse.from_dict(res)
                return droplet_response.droplet, droplet_response.links.actions[0].id
            elif res.get("message") is not None:
                res = Error.from_dict(res)
        elif type(res) is SingleDropletResponse:
            return res.droplet, res.links.actions[0].id
        elif type(res) is Error:
            raise exceptions.APIError(*res.as_dict())

        raise exceptions.Unprocessable(f"Unable to process response from: {res}")

    def get(self, droplet_id: int) -> Droplet:
        """Gets the droplet details.

        Args:
            droplet_id (int): The ID of the droplet to fetch.

        Raises:
            exceptions.BaseHTTPException: For HTTP transport level errors raised by the generated client.
            exceptions.APIError: For errors with the Request.
            exceptions.Unprocessable: In the event the the response could not be processed and no known error was
            handled.

        Returns:
            Droplet: The details of the fetched droplet.
        """

        api = self._client(droplet_id=droplet_id)

        try:
            resp = api.get.droplet()
        except azure_exceptions.HttpResponseError as e:
            raise exceptions.BaseHTTPException(str(e))

        if _handle_error(resp) is Error:
            raise exceptions.APIError(*resp.as_dict())

        if type(resp) is dict:
            if resp.get("droplet") is not None:
                return Droplet.from_dict(resp.get("droplet"))

        if isinstance(resp, DropletResponse):
            return Action.from_dict(resp.droplet)

        raise exceptions.Unprocessable(f"Unable to process `get droplet` response: {resp}")

    def delete(self, droplet_id: int) -> bool:
        """Delets a droplet.

        Args:
            droplet_id (int): The droplet ID.

        Raises:
            exceptions.APIError: An exception with the APIERror details.

        Returns:
            bool: True if the droplet was successfully deleted.
        """

        api = self._client(droplet_id=droplet_id)

        try:
            result = api.destroy.droplet()
        except azure_exceptions.HttpResponseError as e:
            raise exceptions.BaseHTTPException(str(e))

        if type(result) is Error:
            raise exceptions.APIError(*result.as_dict())
        if result is None:
            return True

        return False

    def rename(self, droplet_id: int, new_name: str) -> Action:
        """Initiates a Droplet Rename Action.

        Args:
            droplet_id (int): The ID of the droplet to rename.
            new_name (str): The new name.

        Raises:
            exceptions.BaseHTTPException: For HTTP transport level errors raised by the generated client.
            exceptions.APIError: For errors with the Request.
            exceptions.Unprocessable: In the event the the response could not be processed and no known error was
            handled.

        Returns:
            Action: The details of the initiated Rename Action.
        """

        api = self._client()
        rename = DropletActionRename(type="rename", name=new_name)

        try:
            res = api.post.droplet_action(droplet_id=droplet_id, body=rename)
        except azure_exceptions.HttpResponseError as e:
            raise exceptions.BaseHTTPException(str(e))

        if _handle_error(res) is Error:
            raise exceptions.APIError(*res.as_dict())

        if type(res) is dict:
            if res.get("action") is not None:
                return Action.from_dict(res.get("action"))

        if isinstance(res, DropletActionResponse):
            return Action.from_dict(res.action)

        raise exceptions.Unprocessable(f"Unable to process `rename droplet action` response: {res}")
