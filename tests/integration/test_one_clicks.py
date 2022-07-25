""" Integration Test for 1-clicks"""

import uuid
import pytest
from digitalocean import Client

from tests.integration import defaults, shared


@pytest.mark.parametrize(
    "params,expected_types",
    [
        ({}, {"droplet", "kubernetes"}),
        ({"type": "kubernetes"}, {"kubernetes"}),
        ({"type": "droplet"}, {"droplet"}),
        ({"type": "thisshouldnotmatch"}, None),
    ],
)
def test_one_click_list(integration_client: Client, params: dict, expected_types: set):
    """Test the one_click list operation"""

    list_resp = integration_client.one_clicks.list(**params)

    assert list_resp is not None
    one_clicks = list_resp.get("1_clicks", None)

    if expected_types is None:
        assert one_clicks is None
    else:
        assert one_clicks is not None
        assert isinstance(one_clicks, list)
        assert len(one_clicks) > 0

        returned_types = {i["type"] for i in one_clicks}
        assert returned_types == expected_types


def test_one_click_install_kubernetes_app(integration_client: Client):
    """Test the one_click install_kubernetes operation

    Waits for the cluster state to be `running`.
    Then installs the one_click application.
    Then waits for the install action to complete.
    """

    cluster_create_req = {
        "name": f"{defaults.PREFIX}-cluster-{uuid.uuid4()}",
        "region": defaults.REGION,
        "version": defaults.K8S_VERSION,
        "node_pools": [{"size": defaults.K8S_NODE_SIZE, "count": 2, "name": "workers"}],
    }

    with shared.with_test_kubernetes_cluster(
        integration_client, **cluster_create_req, wait=True
    ) as cluster:
        cluster_id = cluster["kubernetes_cluster"]["id"]

        install_req = {
            "addon_slugs": ["kube-state-metrics", "loki"],
            "cluster_uuid": cluster_id,
        }

        install_resp = integration_client.one_clicks.install_kubernetes(install_req)

        assert install_resp is not None
        assert install_resp["message"] == "Successfully kicked off addon job."
