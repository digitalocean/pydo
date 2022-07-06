"""Mocked tests for kubernetes resources."""
import uuid

import responses


@responses.activate
def test_create_cluster(mock_client, mock_client_url):
    """Mocks the kubernetes create_cluster operation."""

    expected = {
        "kubernetes_cluster": {
            "id": "bd5f5959-5e1e-4205-a714-a914373942af",
            "name": "prod-cluster-01",
            "region": "nyc1",
            "version": "1.18.6-do.0",
            "cluster_subnet": "10.244.0.0/16",
            "service_subnet": "10.245.0.0/16",
            "vpc_uuid": "c33931f2-a26a-4e61-b85c-4e95a2ec431b",
            "ipv4": "",
            "endpoint": "",
            "tags": ["k8s", "k8s:bd5f5959-5e1e-4205-a714-a914373942af"],
            "node_pools": [
                {
                    "id": "cdda885e-7663-40c8-bc74-3a036c66545d",
                    "name": "worker-pool",
                    "size": "s-1vcpu-2gb",
                    "count": 3,
                    "tags": [
                        "k8s",
                        "k8s:bd5f5959-5e1e-4205-a714-a914373942af",
                        "k8s:worker",
                    ],
                    "labels": None,
                    "taints": [],
                    "auto_scale": False,
                    "min_nodes": 0,
                    "max_nodes": 0,
                    "nodes": [
                        {
                            "id": "478247f8-b1bb-4f7a-8db9-2a5f8d4b8f8f",
                            "name": "",
                            "status": {"state": "provisioning"},
                            "droplet_id": "",
                            "created_at": "2018-11-15T16:00:11.000Z",
                            "updated_at": "2018-11-15T16:00:11.000Z",
                        },
                        {
                            "id": "ad12e744-c2a9-473d-8aa9-be5680500eb1",
                            "name": "",
                            "status": {"state": "provisioning"},
                            "droplet_id": "",
                            "created_at": "2018-11-15T16:00:11.000Z",
                            "updated_at": "2018-11-15T16:00:11.000Z",
                        },
                        {
                            "id": "e46e8d07-f58f-4ff1-9737-97246364400e",
                            "name": "",
                            "status": {"state": "provisioning"},
                            "droplet_id": "",
                            "created_at": "2018-11-15T16:00:11.000Z",
                            "updated_at": "2018-11-15T16:00:11.000Z",
                        },
                    ],
                }
            ],
            "maintenance_policy": {
                "start_time": "00:00",
                "duration": "4h0m0s",
                "day": "any",
            },
            "auto_upgrade": False,
            "status": {"state": "provisioning", "message": "provisioning"},
            "created_at": "2018-11-15T16:00:11.000Z",
            "updated_at": "2018-11-15T16:00:11.000Z",
            "surge_upgrade": False,
            "registry_enabled": False,
            "ha": False,
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/kubernetes/clusters",
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
