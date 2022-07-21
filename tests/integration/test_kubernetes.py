""" test_kubernetes.py
    Integration tests for kubernetes.
"""

import uuid

from tests.integration import defaults
from tests.integration import shared
from digitalocean import Client


def test_create_cluster(integration_client: Client):
    """Tests creating a kubernetes cluster

    Waits for the cluster state to be `running`.
    Then tests updating the number of nodes on the node pool.
    Lastly, tests getting the kubeconfig.
    """
    node_pool = "worker-pool"

    create_req = {
        "name": f"{defaults.PREFIX}-cluster-{uuid.uuid4()}",
        "region": defaults.REGION,
        "version": defaults.K8S_VERSION,
        "node_pools": [{"size": defaults.K8S_NODE_SIZE, "count": 2, "name": node_pool}],
    }

    with shared.with_test_kubernetes_cluster(
        integration_client, **create_req
    ) as cluster:
        cluster_id = cluster["kubernetes_cluster"]["id"] or ""
        assert cluster_id != ""
        node_pool_id = cluster["kubernetes_cluster"]["node_pools"][0]["id"] or ""
        assert node_pool_id != ""

        shared.wait_for_kubernetes_cluster_create(integration_client, cluster_id)

        # get the cluster info and verify the state
        get_resp = integration_client.kubernetes.get_cluster(cluster_id)
        assert get_resp["kubernetes_cluster"]["status"]["state"] == "running"

        # update the number of nodes in the node pool
        update_node_pool_resp = integration_client.kubernetes.update_node_pool(
            cluster_id, node_pool_id, {"name": node_pool, "count": 4}
        )
        assert update_node_pool_resp["node_pool"]["count"] == 4

        # get the cluster info again to verify the number of nodes changed
        get_node_pool_resp = integration_client.kubernetes.get_node_pool(
            cluster_id, node_pool
        )
        assert get_node_pool_resp["node_pool"]["count"] == 4

        # get the kubeconfig
        get_kubeconfig_resp = integration_client.kubernetes.get_kubeconfig(
            cluster_id, node_pool_id
        )
        assert get_kubeconfig_resp[:11] == "apiVersion:"
