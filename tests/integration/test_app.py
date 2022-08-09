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
    with shared.with_test_app(
        integration_client,
        {
            "spec": {
                "name": defaults.PREFIX_RANDOM,
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

        assert app["app"]["id"] in [app["id"] for app in list_resp["apps"]]
