# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
"""Customize generated code here.

Follow our quickstart for examples: https://aka.ms/azsdk/python/dpcodegen/python/customize
"""
from typing import TYPE_CHECKING, Any, cast

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
    ResourceNotModifiedError,
    map_error,
)
from azure.core.pipeline import PipelineResponse
from azure.core.tracing.decorator import distributed_trace

from ._operations import (
    KubernetesOperations as _KubernetesOperations,
    build_kubernetes_get_kubeconfig_request,
)

if TYPE_CHECKING:
    # pylint: disable=unused-import,ungrouped-imports
    from typing import MutableMapping, Type


__all__ = ["KubernetesOperations"]


# Override: generated client expects JSON but this endpoint returns application/yaml;
# we return the response body as str instead of deserializing.
class KubernetesOperations(_KubernetesOperations):
    """Kubernetes operations."""

    @distributed_trace
    def get_kubeconfig(
        self, cluster_id: str, *, expiry_seconds: int = 0, **kwargs: Any
    ) -> str:
        """Retrieve the kubeconfig for a Kubernetes Cluster.

        This endpoint returns a kubeconfig file in YAML format. It can be used to
        connect to and administer the cluster using the Kubernetes command line tool,
        ``kubectl``, or other programs supporting kubeconfig files (e.g., client libraries).

        The resulting kubeconfig file uses token-based authentication for clusters
        supporting it, and certificate-based authentication otherwise. For a list of
        supported versions and more information, see "How to Connect to a DigitalOcean
        Kubernetes Cluster"
        https://docs.digitalocean.com/products/kubernetes/how-to/connect-to-cluster/

        Clusters supporting token-based authentication may define an expiration by
        passing a duration in seconds as a query parameter (expiry_seconds).
        If not set or 0, then the token will have a 7 day expiry. The query parameter
        has no impact in certificate-based authentication.

        Kubernetes Roles granted to a user with a token-based kubeconfig are derived from that user's
        DigitalOcean role. Custom roles require additional configuration by a cluster administrator.

        :param cluster_id: A unique ID that can be used to reference a Kubernetes cluster. Required.
        :type cluster_id: str
        :keyword expiry_seconds: The duration in seconds that the returned Kubernetes credentials will
         be valid. If not set or 0, the credentials will have a 7 day expiry. Default value is 0.
        :paramtype expiry_seconds: int
        :return: The kubeconfig file contents as a string (YAML).
        :rtype: str
        :raises ~azure.core.exceptions.HttpResponseError:
        """
        error_map: "MutableMapping[int, Type[HttpResponseError]]" = {
            404: ResourceNotFoundError,
            409: ResourceExistsError,
            304: ResourceNotModifiedError,
            401: cast(
                "Type[HttpResponseError]",
                lambda response: ClientAuthenticationError(response=response),
            ),
            429: HttpResponseError,
            500: HttpResponseError,
        }
        error_map.update(kwargs.pop("error_map", {}) or {})

        _headers = kwargs.pop("headers", {}) or {}
        _params = kwargs.pop("params", {}) or {}

        _request = build_kubernetes_get_kubeconfig_request(
            cluster_id=cluster_id,
            expiry_seconds=expiry_seconds,
            headers=_headers,
            params=_params,
        )
        _request.url = self._client.format_url(_request.url)

        # stream=True so the pipeline's content policy skips deserialization (API returns YAML, not JSON).
        # Without this, the policy raises DecodeError for application/yaml. See test_kubernetes_get_kubeconfig.
        pipeline_response: PipelineResponse = (
            self._client._pipeline.run(  # pylint: disable=protected-access
                _request, stream=True, **kwargs
            )
        )

        response = pipeline_response.http_response

        if response.status_code not in [200]:
            response.read()
            map_error(
                status_code=response.status_code,
                response=response,
                error_map=error_map,
            )
            raise HttpResponseError(response=response)

        body = response.read() if hasattr(response, "read") else response.content
        return body.decode("utf-8") if body else ""


def patch_sdk():
    """Do not remove from this file.

    `patch_sdk` is a last resort escape hatch that allows you to do customizations
    you can't accomplish using the techniques described in
    https://aka.ms/azsdk/python/dpcodegen/python/customize
    """
