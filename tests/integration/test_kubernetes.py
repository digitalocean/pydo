""" test_kubernetes.py
    Integration tests for kubernetes.
"""

from os import environ
from time import sleep
import uuid

import pytest

from tests.integration import defaults
from tests.integration import shared
from pydo import Client
from pydo.exceptions import HttpResponseError

CLUSTER_CREATE_BASIC_REQ = {
    "name": f"{defaults.PREFIX}-cluster-{uuid.uuid4().hex}",
    "region": defaults.REGION,
    "version": defaults.K8S_VERSION,
    "node_pools": [{"size": defaults.K8S_NODE_SIZE, "count": 2, "name": "workers"}],
}


@pytest.fixture(scope="module")
def existing_cluster_id() -> str:
    """Fixture to return get the existing_cluster_id from the environment"""
    return environ.get("DO_EXISTING_CLUSTER_ID", "")


# pylint: disable=redefined-outer-name
def test_kubernetes(integration_client: Client, existing_cluster_id):
    """Tests kubernetes level operations
    (/v2/kubernetes/{...})

    Since creating a kubernetes cluster is a time consuming dependency, this
    test exercises multiple resource operations within one test to take
    advantage of the same cluster.

    This test covers the following top level kubernetes operations:

    1. Creates a new cluster.
    2. Lists all clusters.
    3. Gets the available kubernetes options.
    4. Adds a container registry to kubernetes clusters.
    5. Removes the container registry from kubernetes clusters.
    """
    create_req = CLUSTER_CREATE_BASIC_REQ

    # create_cluster and delete_cluster
    with shared.with_test_kubernetes_cluster(
        integration_client,
        wait=True,
        existing_cluster_id=existing_cluster_id,
        **create_req,
    ) as cluster:
        cluster_id = cluster["kubernetes_cluster"]["id"] or ""
        assert cluster_id != ""

        # list_clusters
        list_resp = integration_client.kubernetes.list_clusters()
        assert "kubernetes_clusters" in list_resp

        # list_options
        opts_resp = integration_client.kubernetes.list_options()
        assert "options" in opts_resp
        options = list(opts_resp["options"].keys())
        assert options == ["regions", "versions", "sizes"]

        # add_registry
        add_reg_resp = integration_client.kubernetes.add_registry(
            {"cluster_uuids": [cluster_id]}
        )
        assert add_reg_resp is None

        # remove_registry
        remove_reg_resp = integration_client.kubernetes.remove_registry(
            {"cluster_uuids": [cluster_id]}
        )
        assert remove_reg_resp is None


def test_kubernetes_clusters(integration_client: Client, existing_cluster_id):
    """Tests operations relating to kubernetes clusters
    (/v2/kubernetes/clusters/{...})

    Since creating a kubernetes cluster is a time consuming dependency, this
    test exercises many resource operations within one test to take advantage
    of the same cluster.

    This test covers the following kubernetes culster level operations:

    1. Creates a new cluster.
    4. Gets the cluster details.
    5. Updates the cluster.
    6. Gets the kubeconfig
    7. Gets the cluster credentials.
    8. Lists associated resources
    9. Attempts to destroy an invalid associated resource
    10. Runs clusterlint
    11. Gets clusterlint
    12. Destroys the cluster
    """
    client: Client = integration_client  # aliasing for shorter lines

    create_req = CLUSTER_CREATE_BASIC_REQ

    # create_cluster and delete_cluster
    with shared.with_test_kubernetes_cluster(
        client, wait=True, existing_cluster_id=existing_cluster_id, **create_req
    ) as cluster:
        cluster_id = cluster["kubernetes_cluster"]["id"] or ""
        assert cluster_id != ""
        node_pool_id = cluster["kubernetes_cluster"]["node_pools"][0]["id"] or ""
        assert node_pool_id != ""

        # get_cluster
        resp = client.kubernetes.get_cluster(cluster_id)
        assert resp["kubernetes_cluster"]["status"]["state"] == "running"

        # update_cluster
        updated_cluster_name = f"cg-updated-{uuid.uuid4().hex}"
        updated_tags = ["k8s", f"k8s:{cluster_id}", "client-gen"]
        resp = client.kubernetes.update_cluster(
            cluster_id,
            {
                "name": updated_cluster_name,
                "tags": updated_tags,
            },
        )
        assert "kubernetes_cluster" in resp and "name" in resp["kubernetes_cluster"]
        assert resp["kubernetes_cluster"]["name"] == updated_cluster_name
        assert set(resp["kubernetes_cluster"]["tags"]) == set(updated_tags)

        # get_kubeconfig
        # TODO: APICLI-1494 - uncomment the following once complete
        # resp = client.kubernetes.get_kubeconfig(cluster_id)
        # assert resp is not None
        # assert resp.decode()[:11] == "apiVersion:"

        # get_credentials
        # TODO: CON-7205 - the expiry_seconds arg can be removed once complete
        # The generated client adds the query parameter regardless of the value.
        # The API currently returns a 500 Server Error if expiry_seconds=0 so
        # this bypasses that scenario.
        resp = client.kubernetes.get_credentials(cluster_id, expiry_seconds=1)
        assert "server" in resp
        assert cluster_id in resp["server"]

        # list_associated_resources
        resp = client.kubernetes.list_associated_resources(cluster_id)
        assert "load_balancers" in resp
        assert "volumes" in resp
        assert "volume_snapshots" in resp

        # destroy_associated_resources_selective
        # Attempt to destroy an invalid resources and expect the client to
        # raise an exception.
        # The API actually returns a 422 Unprocessable Entity but the spec
        # doesn't have 422 defined as an expected response.
        with pytest.raises(HttpResponseError):
            client.kubernetes.destroy_associated_resources_selective(
                cluster_id, {"load_balancers": ["invalid"]}
            )

        # get_cluster_user
        user = client.kubernetes.get_cluster_user(cluster_id)
        assert (
            "kubernetes_cluster_user" in user
            and "username" in user["kubernetes_cluster_user"]
        )
        assert user["kubernetes_cluster_user"]["username"] != ""

        # run_clusterlint
        run_lint = client.kubernetes.run_cluster_lint(cluster_id)
        assert "run_id" in run_lint
        lint_run_id = run_lint.get("run_id", "")
        assert lint_run_id != ""

        sleep(15)

        # get_clusterlint
        get_lint = client.kubernetes.get_cluster_lint_results(
            cluster_id, run_id=lint_run_id
        )
        assert get_lint is not None
        assert get_lint["run_id"] == lint_run_id
        assert isinstance(get_lint["diagnostics"], list)


def test_kubernetes_nodepools(integration_client: Client, existing_cluster_id):
    """Tests operations relating to kubernetes nodepools
    (/v2/kubernetes/clusters/{cluster_id}/node_pools/{...})

    Since creating a kubernetes cluster is a time consuming dependency, this
    test exercises many resource operations within one test to take advantage
    of the same cluster.

    This test covers the following kubernetes culster node pools level
    operations:

    1. Creates a new cluster.
    2. Lists all node pools on the cluster.
    3. Adds a node pool to the cluster.
    4. Gets a a node pool.
    5. Updates a node pool.
    6. Deletes a node pool.


    """
    node_pool = "workers"

    create_req = {
        "name": f"{defaults.PREFIX}-cluster-{uuid.uuid4().hex}",
        "region": defaults.REGION,
        "version": defaults.K8S_VERSION,
        "node_pools": [{"size": defaults.K8S_NODE_SIZE, "count": 2, "name": node_pool}],
    }

    client: Client = integration_client

    with shared.with_test_kubernetes_cluster(
        client, wait=True, existing_cluster_id=existing_cluster_id, **create_req
    ) as cluster:
        cluster_id = cluster["kubernetes_cluster"]["id"] or ""
        assert cluster_id != ""
        node_pool_id = cluster["kubernetes_cluster"]["node_pools"][0]["id"] or ""
        assert node_pool_id != ""

        # list_node_pools
        resp = client.kubernetes.list_node_pools(cluster_id)
        assert "node_pools" in resp
        assert node_pool in [pool["name"] for pool in resp["node_pools"]]

        # add_node_pool
        new_pool_name = "new-pool"
        resp = client.kubernetes.add_node_pool(
            cluster_id,
            {
                "size": "s-1vcpu-2gb",
                "count": 3,
                "name": new_pool_name,
                "tags": ["frontend"],
                "auto_scale": True,
                "min_nodes": 3,
                "max_nodes": 6,
            },
        )
        assert "node_pool" in resp
        assert resp["node_pool"]["name"] == new_pool_name
        new_pool_id = resp["node_pool"]["id"]

        # get_node_pool
        resp = client.kubernetes.get_node_pool(cluster_id, new_pool_id)
        assert "node_pool" in resp
        assert resp["node_pool"]["id"] == new_pool_id

        # update_node_pool
        updated_pool_name = f"{new_pool_name}-{uuid.uuid4().hex}"
        resp = client.kubernetes.update_node_pool(
            cluster_id, new_pool_id, {"name": updated_pool_name, "count": 4}
        )
        assert "node_pool" in resp
        assert resp["node_pool"]["name"] == updated_pool_name
        assert len(resp["node_pool"]["nodes"]) > 0
        node_id = resp["node_pool"]["nodes"][0]["id"]

        # delete_node
        resp = client.kubernetes.delete_node(cluster_id, new_pool_id, node_id)
        assert resp is None

        # delete_node_pool
        resp = client.kubernetes.delete_node_pool(cluster_id, new_pool_id)
        assert resp is None


def test_kubernetes_upgrade_cluster(integration_client: Client, existing_cluster_id):
    """Tests upgrading a cluster"""

    # list_options
    resp = integration_client.kubernetes.list_options()
    assert "options" in resp and "versions" in resp["options"]
    versions = resp["options"]["versions"]
    assert versions is not None

    slugs = sorted([v["slug"] for v in versions])
    assert len(slugs) > 0

    min_version = slugs[0]

    create_req = {
        "name": f"{defaults.PREFIX}-cluster-{uuid.uuid4()}",
        "region": defaults.REGION,
        "version": min_version,
        "node_pools": [{"size": defaults.K8S_NODE_SIZE, "count": 2, "name": "workers"}],
    }
    with shared.with_test_kubernetes_cluster(
        integration_client,
        wait=True,
        existing_cluster_id=existing_cluster_id,
        **create_req,
    ) as cluster:
        cluster_id = cluster["kubernetes_cluster"]["id"]

        # get_available_upgrades
        resp = integration_client.kubernetes.get_available_upgrades(cluster_id)
        assert "available_upgrade_versions" in resp
        assert len(resp["available_upgrade_versions"]) >= 1
        next_version = resp["available_upgrade_versions"][0]["slug"]

        # upgrade_cluster
        resp = integration_client.kubernetes.upgrade_cluster(
            cluster_id, {"version": next_version}
        )
        assert resp is None
