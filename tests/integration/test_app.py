# pylint: disable=line-too-long

""" test_app.py
    Integration tests for apps.
"""

import uuid

from tests.integration import defaults
from tests.integration import shared
from digitalocean import Client


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
            "services": [
                {
                    "name": "api",
                    "git": {
                        "branch": "main",
                        "repo_clone_url": "https://github.com/digitalocean/sample-golang.git",
                    },
                    "run_command": "bin/api",
                    "environment_slug": "go",
                    "instance_count": 2,
                    "instance_size_slug": "professional-xs",
                    "routes": [{"path": "/"}],
                }
            ],
        }
    }

    with shared.with_test_app(integration_client, create_payload) as app:
        list_resp = integration_client.apps.list()

        app_id = app["app"]["id"]

        assert app_id in [app["id"] for app in list_resp["apps"]]

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
