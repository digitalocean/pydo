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

    propose_resp = integration_client.apps.validate_app_spec(create_payload)

    assert propose_resp["app_name_available"] is True

    with shared.with_test_app(integration_client, create_payload) as app:
        list_resp = integration_client.apps.list()

        app_id = app["app"]["id"]

        assert app_id in [app["id"] for app in list_resp["apps"]]

        # An app may not have any alerts once running
        # TODO: figure out how to manually trigger app alerts
        # alerts_resp = integration_client.apps.list_alerts(app_id)

        # assert alerts_resp is not None

        # alert_id = alerts_resp["alerts"][0]["id"]
        # alert_req = {"emails": ["api-engineering@digitalocean.com"]}

        # alert_resp = integration_client.apps.assign_alert_destinations(
        #     app_id, alert_id, alert_req
        # )

        # assert alert_resp is not None

        config = app["app"]["spec"]
        config["region"] = "ams"
        update_payload = {}
        update_payload["spec"] = config

        update_resp = integration_client.apps.update(app_id, update_payload)

        assert update_resp["app"]["spec"]["region"] == "ams"
