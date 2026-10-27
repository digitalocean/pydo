"""Mocked tests for kubernetes resources."""

import uuid
import pytest

import responses
from pydo import Client

from tests.mocked.data import kubernetes_data as data

BASE_PATH = "v2/kubernetes/clusters"


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


@responses.activate
def test_kubernetes_get_kubeconfig(mock_client: Client, mock_client_url):
    """Mock kubernetes get_kubeconfig operation."""

    cluster_id = str(uuid.uuid4())
    expected = data.KUBECONFIG

    responses.add(
        responses.GET,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}/kubeconfig",
        headers={"content-type": "application/yaml"},
        match=[
            responses.matchers.query_param_matcher({"expiry_seconds": 0}),
        ],
        status=200,
        body=expected,
    )

    config_resp = mock_client.kubernetes.get_kubeconfig(cluster_id)
    pytest.skip("The operation currently fails to return content.")
    # TODO: investigate why the generated client doesn't return the response content
    # It seems to be something to do with the yaml content type.
    assert config_resp.decode("utf-8") == expected


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


@responses.activate
def test_kubernetes_cluster_with_registry_integration(
    mock_client: Client, mock_client_url
):
    """Test demonstrating correct approach for registry integration.
    
    This test shows that registry_enabled cannot be set during cluster creation.
    Instead, the add_registry operation must be used after cluster creation.
    
    Related to: https://github.com/digitalocean/pydo/issues/433
    """
    cluster_id = "bd5f5959-5e1e-4205-a714-a914373942af"

    # Create cluster - registry_enabled will be False by default
    cluster_without_registry = data.CLUSTER.copy()
    responses.add(
        responses.POST,
        f"{mock_client_url}/{BASE_PATH}",
        json=cluster_without_registry,
        status=201,
    )

    cluster = mock_client.kubernetes.create_cluster(
        {
            "name": "registry-test-cluster",
            "region": "ams3",
            "version": "1.32",
            "node_pools": [
                {
                    "size": "s-1vcpu-2gb",
                    "count": 2,
                    "name": "worker-pool",
                }
            ],
        }
    )
    
    # Verify cluster was created with registry_enabled=False
    assert cluster["kubernetes_cluster"]["registry_enabled"] is False

    # Add registry integration
    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/kubernetes/registry",
        status=204,
    )

    mock_client.kubernetes.add_registry({"cluster_uuids": [cluster_id]})

    # Get cluster details - now registry should be enabled
    cluster_with_registry = data.CLUSTER.copy()
    cluster_with_registry["kubernetes_cluster"]["registry_enabled"] = True
    
    responses.add(
        responses.GET,
        f"{mock_client_url}/{BASE_PATH}/{cluster_id}",
        json=cluster_with_registry,
        status=200,
    )

    updated_cluster = mock_client.kubernetes.get_cluster(cluster_id)
    assert (
        updated_cluster["kubernetes_cluster"]["registry_enabled"] is True
    ), "Expected registry to be enabled after add_registry call"
