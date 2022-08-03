""" test_monitoring.py
    Integration Tests for Monitoring
"""

import uuid

from digitalocean import Client
from tests.integration import defaults, shared


def test_monitoring_alert_policies(integration_client: Client, public_key: bytes):
    """Tests creating, listing, getting, updating, and deleting an alert policy"""

    droplet_req = {
        "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
        "region": defaults.REGION,
        "size": defaults.DROPLET_SIZE,
        "image": defaults.DROPLET_IMAGE,
        "tags": ["droplet_tag"],
    }

    with shared.with_test_droplet(
        integration_client, public_key, **droplet_req
    ) as droplet:
        shared.wait_for_action(integration_client, droplet["links"]["actions"][0]["id"])
        droplet_get_resp = integration_client.droplets.get(droplet["droplet"]["id"])
        assert droplet_get_resp["droplet"]["status"] == "active"
        droplet_id = droplet_get_resp["droplet"]["id"]

        create_alert_req = {
            "alerts": {
                "email": ["bob@exmaple.com"],
            },
            "compare": "GreaterThan",
            "description": "CPU Alert",
            "enabled": True,
            "entities": [str(droplet_id)],
            "tags": ["droplet_tag"],
            "type": "v1/insights/droplet/cpu",
            "value": 80,
            "window": "5m",
        }

        create_alert_resp = integration_client.monitoring.create_alert_policy(
            body=create_alert_req
        )
        assert create_alert_resp["policy"]["entities"][0] == str(droplet_id)
        alert_uuid = create_alert_resp["policy"]["uuid"]

        # testing listing alert policies
        list_alert_policies = integration_client.monitoring.list_alert_policy()
        assert len(list_alert_policies["policies"]) > 0

        # testing getting alert policies
        get_alert_policies = integration_client.monitoring.get_alert_policy(
            alert_uuid=alert_uuid
        )
        assert get_alert_policies["policy"]["entities"][0] == str(droplet_id)

        update_alert_req = {
            "alerts": {
                "email": ["carl@exmaple.com"],
            },
            "compare": "GreaterThan",
            "description": "CPU Alert",
            "enabled": True,
            "tags": ["droplet_tag"],
            "type": "v1/insights/droplet/cpu",
            "value": 80,
            "window": "5m",
        }

        # testing updating alert policy
        update_alert_policies = integration_client.monitoring.update_alert_policy(
            alert_uuid=alert_uuid, body=update_alert_req
        )
        assert "carl@exmaple.com" in update_alert_policies["policy"]["alerts"]["email"]

        # testing deleting alert policy
        delete_alert_policies = integration_client.monitoring.delete_alert_policy(
            alert_uuid=alert_uuid
        )
        assert delete_alert_policies is None


def test_monitoring_metrics(integration_client: Client, public_key: bytes):
    """Tests Getting Various Metrics"""

    droplet_req = {
        "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
        "region": defaults.REGION,
        "size": defaults.DROPLET_SIZE,
        "image": defaults.DROPLET_IMAGE,
        "tags": ["droplet_tag"],
    }

    with shared.with_test_droplet(
        integration_client, public_key, **droplet_req
    ) as droplet:
        shared.wait_for_action(integration_client, droplet["links"]["actions"][0]["id"])
        droplet_get_resp = integration_client.droplets.get(droplet["droplet"]["id"])
        assert droplet_get_resp["droplet"]["status"] == "active"
        droplet_id = droplet_get_resp["droplet"]["id"]

        # testing getting droplet bandwidth metrics
        bandwidth_metric = integration_client.monitoring.get_droplet_bandwidth_metrics(
            host_id=str(droplet_id),
            interface="public",
            direction="outbound",
            start="1620683817",
            end="1620705417",
        )
        assert bandwidth_metric["status"] == "success"

        # testing getting droplet cpu metrics
        cpu_metric = integration_client.monitoring.get_droplet_cpu_metrics(
            host_id=str(droplet_id), start="1620683817", end="1620705417"
        )
        assert cpu_metric["status"] == "success"

        # testing getting filesystem free metrics
        filesystem_free_metric = (
            integration_client.monitoring.get_droplet_filesystem_free_metrics(
                host_id=str(droplet_id), start="1620683817", end="1620705417"
            )
        )
        assert filesystem_free_metric["status"] == "success"

        # testing getting load1 metrics
        load1_metric = integration_client.monitoring.get_droplet_load1_metrics(
            host_id=str(droplet_id), start="1620683817", end="1620705417"
        )
        assert load1_metric["status"] == "success"

        # testing getting load5 metrics
        load5_metric = integration_client.monitoring.get_droplet_load5_metrics(
            host_id=str(droplet_id), start="1620683817", end="1620705417"
        )
        assert load5_metric["status"] == "success"

        # testing getting load15 metrics
        load15_metric = integration_client.monitoring.get_droplet_load15_metrics(
            host_id=str(droplet_id), start="1620683817", end="1620705417"
        )
        assert load15_metric["status"] == "success"

        # testing getting droplet memory cached
        memory_cached_metric = (
            integration_client.monitoring.get_droplet_memory_cached_metrics(
                host_id=str(droplet_id), start="1620683817", end="1620705417"
            )
        )
        assert memory_cached_metric["status"] == "success"

        # testing getting droplet free memory
        memory_free_metric = (
            integration_client.monitoring.get_droplet_memory_free_metrics(
                host_id=str(droplet_id), start="1620683817", end="1620705417"
            )
        )
        assert memory_free_metric["status"] == "success"

        # testing getting droplet total memory
        memory_total_metric = (
            integration_client.monitoring.get_droplet_memory_total_metrics(
                host_id=str(droplet_id), start="1620683817", end="1620705417"
            )
        )
        assert memory_total_metric["status"] == "success"

        # testing getting droplet available memory
        memory_available_metric = (
            integration_client.monitoring.get_droplet_memory_available_metrics(
                host_id=str(droplet_id), start="1620683817", end="1620705417"
            )
        )
        assert memory_available_metric["status"] == "success"
