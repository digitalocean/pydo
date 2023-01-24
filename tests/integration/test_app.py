# pylint: disable=line-too-long

""" test_app.py
    Integration tests for apps.
"""

import uuid

from tests.integration import defaults
from tests.integration import shared
from pydo import Client


def test_app_lifecycle(integration_client: Client):
    """Tests the entire lifecycle of an app
    Creates
    Lists
    Updates
    Deletes
    """
    name = f"{defaults.PREFIX}-{uuid.uuid4().hex[:10]}"
    create_payload = {
        "spec": {
            "name": name,
            "region": "nyc",
            "alerts": [{"rule": "DEPLOYMENT_LIVE"}],
            "services": [
                {
                    "name": "api",
                    "git": {
                        "branch": "main",
                        "repo_clone_url": "https://github.com/digitalocean/sample-golang.git",
                    },
                    "environment_slug": "go",
                    "instance_count": 2,
                    "instance_size_slug": "professional-xs",
                    "routes": [{"path": "/"}],
                }
            ],
        }
    }

    propose_resp = integration_client.apps.validate_app_spec(create_payload)

    assert propose_resp["app_name_available"] is True

    with shared.with_test_app(integration_client, create_payload) as app:
        list_resp = integration_client.apps.list()

        app_id = app["app"]["id"]

        assert app_id in [app["id"] for app in list_resp["apps"]]

        # An app may not have any alerts once running
        alerts_resp = integration_client.apps.list_alerts(app_id)

        assert alerts_resp is not None
        assert alerts_resp["alerts"][0]["spec"]["rule"] == "DEPLOYMENT_LIVE"

        alert_id = alerts_resp["alerts"][0]["id"]

        # assign_alert_destinations requires an email address that has access to the app
        account_resp = integration_client.account.get()
        assert account_resp is not None
        alert_req = {"emails": [account_resp["account"]["email"]]}

        alert_resp = integration_client.apps.assign_alert_destinations(
            app_id, alert_id, alert_req
        )

        assert alert_resp is not None

        config = app["app"]["spec"]
        config["region"] = "ams"
        update_payload = {}
        update_payload["spec"] = config

        update_resp = integration_client.apps.update(app_id, update_payload)

        assert update_resp["app"]["spec"]["region"] == "ams"


def test_app_info(integration_client: Client):
    """Tests all information endpoints"""

    list_app_tier = integration_client.apps.list_tiers()

    assert len(list_app_tier["tiers"]) >= 3

    get_app_tier = integration_client.apps.get_tier("basic")

    assert get_app_tier["tier"]["slug"] == "basic"

    list_instance_sizes = integration_client.apps.list_instance_sizes()

    assert len(list_instance_sizes["instance_sizes"]) >= 4

    get_instance_size = integration_client.apps.get_instance_size("basic-xxs")

    assert get_instance_size["instance_size"]["slug"] == "basic-xxs"

    list_regions = integration_client.apps.list_regions()

    assert len(list_regions["regions"]) >= 5


def test_app_metrics_list_bandwidth_daily(integration_client: Client):
    """Tests listing the bandwidth_day metrics for multiple apps"""

    name1 = f"{defaults.PREFIX}-{uuid.uuid4().hex[:10]}"
    name2 = f"{defaults.PREFIX}-{uuid.uuid4().hex[:10]}"

    create_app_req1 = {
        "spec": {
            "name": name1,
            "region": "nyc",
            "alerts": [{"rule": "DEPLOYMENT_LIVE"}],
            "services": [
                {
                    "name": "api",
                    "git": {
                        "branch": "main",
                        "repo_clone_url": "https://github.com/digitalocean/sample-golang.git",
                    },
                    "environment_slug": "go",
                    "instance_count": 2,
                    "instance_size_slug": "professional-xs",
                    "routes": [{"path": "/"}],
                }
            ],
        }
    }

    create_app_req2 = {
        "spec": {
            "name": name2,
            "region": "nyc",
            "alerts": [{"rule": "DEPLOYMENT_LIVE"}],
            "services": [
                {
                    "name": "api",
                    "git": {
                        "branch": "main",
                        "repo_clone_url": "https://github.com/digitalocean/sample-golang.git",
                    },
                    "environment_slug": "go",
                    "instance_count": 2,
                    "instance_size_slug": "professional-xs",
                    "routes": [{"path": "/"}],
                }
            ],
        }
    }

    with shared.with_test_app(integration_client, create_app_req1) as test_app_resp1:
        with shared.with_test_app(
            integration_client, create_app_req2
        ) as test_app_resp2:
            app_id1 = test_app_resp1["app"]["id"]
            app_id2 = test_app_resp2["app"]["id"]

            metrics_resp = integration_client.apps.list_metrics_bandwidth_daily(
                {"app_ids": [app_id1, app_id2]}
            )

            assert "app_bandwidth_usage" in metrics_resp.keys()
            resp_app_ids = [
                metrics["app_id"] for metrics in metrics_resp["app_bandwidth_usage"]
            ]
            assert app_id1 in resp_app_ids
            assert app_id2 in resp_app_ids


def test_app_metrics_get_bandwidth_daily(integration_client: Client):
    """Tests getting the bandwidth_daily metrics for one app"""

    create_app_req = {
        "spec": {
            "name": f"{defaults.PREFIX}-{uuid.uuid4().hex[:10]}",
            "region": "nyc",
            "alerts": [{"rule": "DEPLOYMENT_LIVE"}],
            "services": [
                {
                    "name": "api",
                    "git": {
                        "branch": "main",
                        "repo_clone_url": "https://github.com/digitalocean/sample-golang.git",
                    },
                    "environment_slug": "go",
                    "instance_count": 2,
                    "instance_size_slug": "professional-xs",
                    "routes": [{"path": "/"}],
                }
            ],
        }
    }
    with shared.with_test_app(integration_client, create_app_req) as test_app_resp:
        app_id = test_app_resp["app"]["id"]
        metrics_resp = integration_client.apps.get_metrics_bandwidth_daily(app_id)

        assert "app_bandwidth_usage" in metrics_resp.keys()
        assert metrics_resp["app_bandwidth_usage"][0]["app_id"] == app_id
