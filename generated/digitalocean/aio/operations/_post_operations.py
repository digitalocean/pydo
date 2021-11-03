# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator (autorest: 3.4.0, generator: @autorest/python@5.7.0)
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
from typing import Any, Callable, Dict, Generic, Optional, TypeVar, Union
import warnings

from azure.core.exceptions import ClientAuthenticationError, HttpResponseError, ResourceExistsError, ResourceNotFoundError, map_error
from azure.core.pipeline import PipelineResponse
from azure.core.pipeline.transport import AsyncHttpResponse, HttpRequest

from ... import models as _models

T = TypeVar('T')
ClsType = Optional[Callable[[PipelineResponse[HttpRequest, AsyncHttpResponse], T, Dict[str, Any]], Any]]

class PostOperations:
    """PostOperations async operations.

    You should not instantiate this class directly. Instead, you should create a Client instance that
    instantiates it for you and attaches it as an attribute.

    :ivar models: Alias to model classes used in this operation group.
    :type models: ~digitalocean.models
    :param client: Client for service requests.
    :param config: Configuration of service client.
    :param serializer: An object model serializer.
    :param deserializer: An object model deserializer.
    """

    models = _models

    def __init__(self, client, config, serializer, deserializer) -> None:
        self._client = client
        self._serialize = serializer
        self._deserialize = deserializer
        self._config = config

    async def droplet_action(
        self,
        droplet_id: object,
        body: Optional[object] = None,
        **kwargs
    ) -> Union["_models.Components1Sllx9CResponsesDropletActionContentApplicationJsonSchema", "_models.Error"]:
        """Initiate a Droplet Action.

        To initiate an action on a Droplet send a POST request to
        ``/v2/droplets/$DROPLET_ID/actions``. In the JSON body to the request,
        set the ``type`` attribute to on of the supported action types:

        .. list-table::
           :header-rows: 1

           * - Action
             - Details
           * - :code:`<nobr>`enable_backups`</nobr>`
             - Enables backups for a Droplet
           * - :code:`<nobr>`disable_backups`</nobr>`
             - Disables backups for a Droplet
           * - :code:`<nobr>`reboot`</nobr>`
             - Reboots a Droplet. A ``reboot`` action is an attempt to reboot the Droplet in a graceful
        way, similar to using the ``reboot`` command from the console.
           * - :code:`<nobr>`power_cycle`</nobr>`
             - Power cycles a Droplet. A ``powercycle`` action is similar to pushing the reset button
        on a physical machine, it's similar to booting from scratch.
           * - :code:`<nobr>`shutdown`</nobr>`
             - Shutsdown a Droplet. A shutdown action is an attempt to shutdown the Droplet in a
        graceful way, similar to using the ``shutdown`` command from the console. Since a ``shutdown``
        command can fail, this action guarantees that the command is issued, not that it succeeds. The
        preferred way to turn off a Droplet is to attempt a shutdown, with a reasonable timeout,
        followed by a ``power_off`` action to ensure the Droplet is off.
           * - :code:`<nobr>`power_off`</nobr>`
             - Powers off a Droplet. A ``power_off`` event is a hard shutdown and should only be used
        if the ``shutdown`` action is not successful. It is similar to cutting the power on a server
        and could lead to complications.
           * - :code:`<nobr>`power_on`</nobr>`
             - Powers on a Droplet.
           * - :code:`<nobr>`restore`</nobr>`
             - Restore a Droplet using a backup image. The image ID that is passed in must be a backup
        of the current Droplet instance. The operation will leave any embedded SSH keys intact.
           * - :code:`<nobr>`password_reset`</nobr>`
             - Resets the root password for a Droplet. A new password will be provided via email. It
        must be changed after first use.
           * - :code:`<nobr>`resize`</nobr>`
             - Resizes a Droplet. Set the ``size`` attribute to a size slug. If a permanent resize with
        disk changes included is desired, set the ``disk`` attribute to ``true``.
           * - :code:`<nobr>`rebuild`</nobr>`
             - Rebuilds a Droplet from a new base image. Set the ``image`` attribute to an image ID or
        slug.
           * - :code:`<nobr>`rename`</nobr>`
             - Renames a Droplet.
           * - :code:`<nobr>`change_kernel`</nobr>`
             - Changes a Droplet's kernel. Only applies to Droplets with externally managed kernels.
        All Droplets created after March 2017 use internal kernels by default.
           * - :code:`<nobr>`enable_ipv6`</nobr>`
             - Enables IPv6 for a Droplet.
           * - :code:`<nobr>`snapshot`</nobr>`
             - Takes a snapshot of a Droplet.

        :param droplet_id: A unique number (id) or string (slug) used to identify and reference a
         specific droplet.
        :type droplet_id: object
        :param body: The ``type`` attribute set in the request body will specify the  action that
         will be taken on the Droplet. Some actions will require additional
         attributes to be set as well.
        :type body: object
        :keyword callable cls: A custom type or function that will be passed the direct response
        :return: Components1Sllx9CResponsesDropletActionContentApplicationJsonSchema or Error, or the result of cls(response)
        :rtype: ~digitalocean.models.Components1Sllx9CResponsesDropletActionContentApplicationJsonSchema or ~digitalocean.models.Error
        :raises: ~azure.core.exceptions.HttpResponseError
        """
        cls = kwargs.pop('cls', None)  # type: ClsType[Union["_models.Components1Sllx9CResponsesDropletActionContentApplicationJsonSchema", "_models.Error"]]
        error_map = {
            401: ClientAuthenticationError, 404: ResourceNotFoundError, 409: ResourceExistsError
        }
        error_map.update(kwargs.pop('error_map', {}))
        content_type = kwargs.pop("content_type", "application/json")
        accept = "application/json"

        # Construct URL
        url = self.droplet_action.metadata['url']  # type: ignore
        path_format_arguments = {
            'droplet_id': self._serialize.url("droplet_id", droplet_id, 'object'),
        }
        url = self._client.format_url(url, **path_format_arguments)

        # Construct parameters
        query_parameters = {}  # type: Dict[str, Any]

        # Construct headers
        header_parameters = {}  # type: Dict[str, Any]
        header_parameters['Content-Type'] = self._serialize.header("content_type", content_type, 'str')
        header_parameters['Accept'] = self._serialize.header("accept", accept, 'str')

        body_content_kwargs = {}  # type: Dict[str, Any]
        if body is not None:
            body_content = self._serialize.body(body, 'object')
        else:
            body_content = None
        body_content_kwargs['content'] = body_content
        request = self._client.post(url, query_parameters, header_parameters, **body_content_kwargs)
        pipeline_response = await self._client._pipeline.run(request, stream=False, **kwargs)
        response = pipeline_response.http_response

        if response.status_code not in [201, 401, 404, 429, 500]:
            map_error(status_code=response.status_code, response=response, error_map=error_map)
            raise HttpResponseError(response=response)

        response_headers = {}
        if response.status_code == 201:
            response_headers['ratelimit-limit']=self._deserialize('int', response.headers.get('ratelimit-limit'))
            response_headers['ratelimit-remaining']=self._deserialize('int', response.headers.get('ratelimit-remaining'))
            response_headers['ratelimit-reset']=self._deserialize('int', response.headers.get('ratelimit-reset'))
            deserialized = self._deserialize('Components1Sllx9CResponsesDropletActionContentApplicationJsonSchema', pipeline_response)

        if response.status_code == 401:
            response_headers['ratelimit-limit']=self._deserialize('int', response.headers.get('ratelimit-limit'))
            response_headers['ratelimit-remaining']=self._deserialize('int', response.headers.get('ratelimit-remaining'))
            response_headers['ratelimit-reset']=self._deserialize('int', response.headers.get('ratelimit-reset'))
            deserialized = self._deserialize('Error', pipeline_response)

        if response.status_code == 404:
            response_headers['ratelimit-limit']=self._deserialize('int', response.headers.get('ratelimit-limit'))
            response_headers['ratelimit-remaining']=self._deserialize('int', response.headers.get('ratelimit-remaining'))
            response_headers['ratelimit-reset']=self._deserialize('int', response.headers.get('ratelimit-reset'))
            deserialized = self._deserialize('Error', pipeline_response)

        if response.status_code == 429:
            response_headers['ratelimit-limit']=self._deserialize('int', response.headers.get('ratelimit-limit'))
            response_headers['ratelimit-remaining']=self._deserialize('int', response.headers.get('ratelimit-remaining'))
            response_headers['ratelimit-reset']=self._deserialize('int', response.headers.get('ratelimit-reset'))
            deserialized = self._deserialize('Error', pipeline_response)

        if response.status_code == 500:
            response_headers['ratelimit-limit']=self._deserialize('int', response.headers.get('ratelimit-limit'))
            response_headers['ratelimit-remaining']=self._deserialize('int', response.headers.get('ratelimit-remaining'))
            response_headers['ratelimit-reset']=self._deserialize('int', response.headers.get('ratelimit-reset'))
            deserialized = self._deserialize('Error', pipeline_response)

        if cls:
            return cls(pipeline_response, deserialized, response_headers)

        return deserialized
    droplet_action.metadata = {'url': '/v2/droplets/{droplet_id}/actions'}  # type: ignore