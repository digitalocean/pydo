"""Mocked tests for kubernetes resources."""

import re
import uuid
from unittest.mock import patch

import pytest

import responses
from azure.core.exceptions import DecodeError, ResourceNotFoundError

from pydo import Client
from pydo.operations._operations import (
    KubernetesOperations as _GeneratedKubernetesOperations,
)

from tests.mocked.data import kubernetes_data as data

BASE_PATH = "v2/kubernetes/clusters"

# URL pattern for kubeconfig so the mock matches the actual request (with query string)
KUBECONFIG_URL_PATTERN = re.compile(
    r"https://testing\.local/v2/kubernetes/clusters/[^/]+/kubeconfig\?expiry_seconds=0"
)


@responses.activate
def test_kubernetes_list_clusters(mock_client: Client, mock_client_url):
    """Mocks the kubernetes list operation."""

    expected = [data.CLUSTER]

    responses.add(
        responses.GET,
        f"{mock_client_url}/{BASE_PATH}",
        json=expected,
        status=200,
    )

    list_resp = mock_client.kubernetes.list_clusters()
    assert list_resp == expected


@responses.activate
def test_kubernetes_create_cluster(mock_client: Client, mock_client_url):
    """Mocks the kubernetes create_cluster operation."""

    expected = data.CLUSTER

    responses.add(
        responses.POST,
        f"{mock_client_url}/{BASE_PATH}",
        json=expected,
        status=201,
    )

    resp = mock_client.kubernetes.create_cluster(
        {
            "name": f"fake-cluster-{uuid.uuid4()}",
            "region": "nyc1",
            "version": "latest",
            "node_pools": [
                {
                    "size": "fake-size",
                    "count": 4,
                    "name": "worker-pool",
                }
            ],
        }
    )

    assert resp == expected


@responses.activate
def test_kubernetes_get_cluster(mock_client: Client, mock_client_url):
    """Mock kubernetes get cluster operation."""

    cluster_id = str(uuid.uuid4())
    expected = data.CLUSTER

    responses.add(
        responses.GET,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}",
        json=expected,
        status=200,
    )

    list_resp = mock_client.kubernetes.get_cluster(cluster_id)
    assert list_resp == expected


@responses.activate
def test_kubernetes_update_cluster(mock_client: Client, mock_client_url):
    """Mock kubernetes update_cluster operation."""

    cluster_id = str(uuid.uuid4())
    expected = data.CLUSTER

    responses.add(
        responses.PUT,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}",
        json=expected,
        status=202,
    )

    update_resp = mock_client.kubernetes.update_cluster(
        cluster_id,
        {
            "name": "prod-cluster-01",
            "tags": [
                "k8s",
                "k8s:bd5f5959-5e1e-4205-a714-a914373942af",
                "production",
                "web-team",
            ],
            "maintenance_policy": {"start_time": "12:00", "day": "any"},
            "auto_upgrade": True,
            "surge_upgrade": True,
        },
    )
    assert update_resp == expected


@responses.activate
def test_kubernetes_delete_cluster(mock_client: Client, mock_client_url):
    """Mock kubernetes delete_cluster operation."""

    cluster_id = str(uuid.uuid4())

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}",
        status=204,
    )

    del_resp = mock_client.kubernetes.delete_cluster(cluster_id)
    assert del_resp is None


@responses.activate
def test_kubernetes_list_associated_resources(mock_client: Client, mock_client_url):
    """Mock kubernetes list_associated_resources operation."""

    cluster_id = str(uuid.uuid4())
    expected = data.ASSOCIATED_RESOURCES

    responses.add(
        responses.GET,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/destroy_with_associated_resources",
        status=200,
        json=expected,
    )

    list_resp = mock_client.kubernetes.list_associated_resources(cluster_id)
    assert list_resp == expected


@responses.activate
def test_kubernetes_destroy_associated_resources_selective(
    mock_client: Client, mock_client_url
):
    """Mock kubernetes destroy_associated_resources_selective operation."""

    cluster_id = str(uuid.uuid4())

    responses.add(
        responses.DELETE,
        (
            f"{mock_client_url}/{BASE_PATH}/{cluster_id}"
            "/destroy_with_associated_resources/selective"
        ),
        status=204,
    )

    des_resp = mock_client.kubernetes.destroy_associated_resources_selective(
        cluster_id,
        {
            "load_balancers": ["4de7ac8b-495b-4884-9a69-1050c6793cd6"],
            "volumes": ["ba49449a-7435-11ea-b89e-0a58ac14480f"],
            "volume_snapshots": ["edb0478d-7436-11ea-86e6-0a58ac144b91"],
        },
    )
    assert des_resp is None


@responses.activate
def test_kubernetes_destroy_associated_resources_dangerous(
    mock_client: Client, mock_client_url
):
    """Mock kubernetes destroy_associated_resources_dangerous operation."""

    cluster_id = str(uuid.uuid4())

    responses.add(
        responses.DELETE,
        (
            f"{mock_client_url}/{BASE_PATH}/{cluster_id}"
            "/destroy_with_associated_resources/dangerous"
        ),
        status=204,
    )

    des_resp = mock_client.kubernetes.destroy_associated_resources_dangerous(cluster_id)
    assert des_resp is None


def _kubeconfig_yaml_callback(_request):
    """Return 200 with body as YAML and Content-Type: application/yaml only.

    The responses library can merge headers and yield e.g. "text/plain,
    application/yaml", which the pipeline treats as text/plain and does not
    raise DecodeError. A callback ensures the response has exactly
    application/yaml so the content policy fails (matching real API behaviour).
    """
    return (200, {"Content-Type": "application/yaml"}, data.KUBECONFIG)


@responses.activate
def test_kubernetes_get_kubeconfig_generated_raises_decode_error(mock_client: Client):
    """Without our override, get_kubeconfig with application/yaml raises DecodeError.

    The mock uses a callback so Content-Type is exactly application/yaml (no
    text/plain). That makes the pipeline's content policy try to deserialize and
    raise DecodeError, matching the real API. Our override (stream=True + return
    body as text) fixes this. If this test fails, the issue was likely fixed
    upstream and the override can be removed.
    """
    cluster_id = str(uuid.uuid4())
    # Regex so the mock matches the actual request URL including ?expiry_seconds=0
    responses.add_callback(
        responses.GET,
        KUBECONFIG_URL_PATTERN,
        callback=_kubeconfig_yaml_callback,
    )
    # Use generated (unpatched) operations so the pipeline tries to deserialize YAML
    # pylint: disable=protected-access
    generated_ops = _GeneratedKubernetesOperations(
        mock_client.kubernetes._client,
        mock_client._config,
        mock_client._serialize,
        mock_client._deserialize,
    )
    with pytest.raises(DecodeError):
        generated_ops.get_kubeconfig(cluster_id)


@responses.activate
def test_kubernetes_get_kubeconfig(mock_client: Client):
    """Mock kubernetes get_kubeconfig operation.

    The patched client returns the response body as a string (YAML). The mock uses
    the same callback as test_kubernetes_get_kubeconfig_generated_raises_decode_error
    (Content-Type: application/yaml only) so behaviour matches the real API.
    """
    cluster_id = str(uuid.uuid4())
    expected = data.KUBECONFIG

    responses.add_callback(
        responses.GET,
        KUBECONFIG_URL_PATTERN,
        callback=_kubeconfig_yaml_callback,
    )

    # Regression: override must use stream=True or pipeline deserializes and fails
    # pylint: disable=protected-access
    pipeline = mock_client.kubernetes._client._pipeline
    with patch.object(pipeline, "run", wraps=pipeline.run) as run_mock:
        config_resp = mock_client.kubernetes.get_kubeconfig(cluster_id)
        run_mock.assert_called_once()
        assert run_mock.call_args[1]["stream"] is True, (
            "get_kubeconfig must call pipeline.run(..., stream=True) so the "
            "content policy skips deserialization (API returns application/yaml)."
        )
    assert isinstance(config_resp, str)
    assert config_resp == expected


@responses.activate
def test_kubernetes_get_kubeconfig_404_raises(mock_client: Client, mock_client_url):
    """get_kubeconfig raises ResourceNotFoundError on 404."""
    cluster_id = str(uuid.uuid4())
    responses.add(
        responses.GET,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/kubeconfig",
        json={"id": "not_found", "message": "Cluster not found"},
        status=404,
    )
    with pytest.raises(ResourceNotFoundError):
        mock_client.kubernetes.get_kubeconfig(cluster_id)


@responses.activate
def test_kubernetes_get_credentials(mock_client: Client, mock_client_url):
    """Mock kubernetes get_credentials operation."""

    cluster_id = str(uuid.uuid4())
    expected = data.CREDENTIALS

    responses.add(
        responses.GET,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/credentials",
        match=[
            responses.matchers.query_param_matcher({"expiry_seconds": 0}),
        ],
        status=200,
        json=expected,
    )

    creds_resp = mock_client.kubernetes.get_credentials(cluster_id)
    assert creds_resp == expected


@responses.activate
def test_kubernetes_get_available_upgrades(mock_client: Client, mock_client_url):
    """Mock kubernetes available_upgrades operation."""

    cluster_id = str(uuid.uuid4())
    expected = data.AVAILABLE_UPGRADES

    responses.add(
        responses.GET,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/upgrades",
        status=200,
        json=expected,
    )

    upgrades_resp = mock_client.kubernetes.get_available_upgrades(cluster_id)
    assert upgrades_resp == expected


@responses.activate
def test_kubernetes_upgrade_cluster(mock_client: Client, mock_client_url):
    """Mock kubernetes upgrade_cluster operation."""

    cluster_id = str(uuid.uuid4())

    responses.add(
        responses.POST,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/upgrade",
        status=202,
    )

    upgrade_resp = mock_client.kubernetes.upgrade_cluster(
        cluster_id, {"version": "1.16.13-do.0"}
    )
    assert upgrade_resp is None


@responses.activate
def test_kubernetes_list_node_pools(mock_client: Client, mock_client_url):
    """Mock kubernetes list_node_pools operation."""

    cluster_id = str(uuid.uuid4())
    expected = data.NODE_POOLS

    responses.add(
        responses.GET,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/node_pools",
        status=200,
        json=expected,
    )

    node_pools_resp = mock_client.kubernetes.list_node_pools(cluster_id)
    assert node_pools_resp == expected


@responses.activate
def test_kubernetes_add_node_pool(mock_client: Client, mock_client_url):
    """Mock kubernetes add_node_pool operation."""

    cluster_id = str(uuid.uuid4())
    expected = data.NODE_POOL

    responses.add(
        responses.POST,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/node_pools",
        status=201,
        json=expected,
    )

    node_pool_resp = mock_client.kubernetes.add_node_pool(
        cluster_id,
        {
            "size": "s-1vcpu-2gb",
            "count": 3,
            "name": "new-pool",
            "tags": ["frontend"],
            "auto_scale": True,
            "min_nodes": 3,
            "max_nodes": 6,
        },
    )
    assert node_pool_resp == expected


@responses.activate
def test_kubernetes_get_node_pool(mock_client: Client, mock_client_url):
    """Mock kubernetes get_node_pool operation."""

    cluster_id = str(uuid.uuid4())
    node_pool_id = str(uuid.uuid4())
    expected = data.NODE_POOL

    responses.add(
        responses.GET,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/node_pools/{node_pool_id}",
        status=200,
        json=expected,
    )

    node_pool_resp = mock_client.kubernetes.get_node_pool(cluster_id, node_pool_id)
    assert node_pool_resp == expected


@responses.activate
def test_kubernetes_update_node_pool(mock_client: Client, mock_client_url):
    """Mock kubernetes update_node_pool operation."""

    cluster_id = str(uuid.uuid4())
    node_pool_id = str(uuid.uuid4())
    expected = data.NODE_POOL

    responses.add(
        responses.PUT,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/node_pools/{node_pool_id}",
        status=202,
        json=expected,
    )

    update_resp = mock_client.kubernetes.update_node_pool(
        cluster_id,
        node_pool_id,
        {
            "name": "frontend-pool",
            "count": 3,
            "tags": [
                "k8s",
                "k8s:bd5f5959-5e1e-4205-a714-a914373942af",
                "k8s-worker",
                "production",
                "web-team",
            ],
            "labels": None,
            "taints": [{"key": "priority", "value": "high", "effect": "NoSchedule"}],
            "auto_scale": True,
            "min_nodes": 3,
            "max_nodes": 6,
        },
    )
    assert update_resp == expected


@responses.activate
def test_kubernetes_delete_node_pool(mock_client: Client, mock_client_url):
    """Mock kubernetes delete_node_pool operation."""

    cluster_id = str(uuid.uuid4())
    node_pool_id = str(uuid.uuid4())

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/node_pools/{node_pool_id}",
        status=204,
    )

    del_resp = mock_client.kubernetes.delete_node_pool(cluster_id, node_pool_id)
    assert del_resp is None


@responses.activate
def test_kubernetes_delete_node(mock_client: Client, mock_client_url):
    """Mock kubernetes delete_node operation."""

    cluster_id = str(uuid.uuid4())
    node_pool_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/node_pools/{node_pool_id}/nodes/{node_id}",  # pylint: disable=line-too-long
        status=202,
        match=[
            responses.matchers.query_param_matcher({"skip_drain": 0, "replace": 0}),
        ],
    )

    del_resp = mock_client.kubernetes.delete_node(cluster_id, node_pool_id, node_id)
    assert del_resp is None


@responses.activate
def test_kubernetes_get_user_info(mock_client: Client, mock_client_url):
    """Mock kubernetes get_user_info operation."""

    cluster_id = str(uuid.uuid4())

    responses.add(
        responses.GET,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/user",
        status=200,
    )

    user_resp = mock_client.kubernetes.get_cluster_user(cluster_id)
    assert user_resp is None


@responses.activate
def test_kubernetes_list_options(mock_client: Client, mock_client_url):
    """Mock kubernetes list_options operation."""

    expected = data.OPTIONS

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/kubernetes/options",
        status=200,
        json=expected,
    )

    options_resp = mock_client.kubernetes.list_options()
    assert options_resp == expected


@responses.activate
def test_kubernetes_run_clusterlint(mock_client: Client, mock_client_url):
    """Mock kubernetes run_clusterlint operation."""

    cluster_id = str(uuid.uuid4())
    expected = {"run_id": "50c2f44c-011d-493e-aee5-361a4a0d1844"}

    responses.add(
        responses.POST,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/clusterlint",
        status=202,
        json=expected,
    )

    lint_resp = mock_client.kubernetes.run_cluster_lint(cluster_id)
    assert lint_resp == expected


@responses.activate
def test_kubernetes_get_clusterlint(mock_client: Client, mock_client_url):
    """Mock kubernetes get_clusterlint operation."""

    cluster_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    expected = data.CLUSTER_LINT

    responses.add(
        responses.GET,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/clusterlint",
        status=200,
        match=[
            responses.matchers.query_param_matcher({"run_id": run_id}),
        ],
        json=expected,
    )

    lint_resp = mock_client.kubernetes.get_cluster_lint_results(
        cluster_id, run_id=run_id
    )
    assert lint_resp == expected


@responses.activate
def test_kubernetes_add_container_registry(mock_client: Client, mock_client_url):
    """Mock kubernetes add_container_registry operation."""

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/kubernetes/registry",
        status=204,
    )

    add_reg_resp = mock_client.kubernetes.add_registry(
        {
            "cluster_uuids": [
                "bd5f5959-5e1e-4205-a714-a914373942af",
                "50c2f44c-011d-493e-aee5-361a4a0d1844",
            ]
        }
    )
    assert add_reg_resp is None


@responses.activate
def test_kubernetes_remove_container_registry(mock_client: Client, mock_client_url):
    """Mock kubernetes remove_container_registry operation."""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/kubernetes/registry",
        status=204,
    )

    add_reg_resp = mock_client.kubernetes.remove_registry(
        {
            "cluster_uuids": [
                "bd5f5959-5e1e-4205-a714-a914373942af",
                "50c2f44c-011d-493e-aee5-361a4a0d1844",
            ]
        }
    )
    assert add_reg_resp is None
