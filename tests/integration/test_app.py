""" test_app.py
    Integration tests for apps.
"""

import uuid

from tests.integration import shared
from digitalocean import Client
from tests.integration import defaults


def test_app_lifecycle(integration_client: Client):
    """Tests the entire lifecycle of an app
    Creates
    Lists
    Updates
    Deletes
    """
    name = f"{defaults.PREFIX}-{uuid.uuid4().hex[:10]}"
    with shared.with_test_app(
        integration_client,
        {
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
        },
    ) as app:
        list_resp = integration_client.apps.list()

        Id = app["app"]["id"]

        assert Id in [app["id"] for app in list_resp["apps"]]

        config = app["app"]["spec"]
        config["region"] = "ams"
        update_payload = {}
        update_payload["spec"] = config

        update_resp = integration_client.apps.update(Id, update_payload)

        assert update_resp["app"]["spec"]["region"] == "ams"
