# pylint: disable=duplicate-code
# pylint: disable=line-too-long
""" test_app_deployment.py
    Integration tests for app deployments
"""

import time
import uuid
from tests.integration import defaults
from tests.integration import shared
from digitalocean import Client


def test_app_deployment_lifecycle(integration_client: Client):
    """Tests the app deployment endpoints"""

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
        app_id = app["app"]["id"]
        app_deployment = integration_client.apps.create_deployment(
            app_id, {"force_build": True}
        )

        deployment_id = app_deployment["deployment"]["id"]

        list_deployments = integration_client.apps.list_deployments(app_id)

        assert deployment_id in [
            deployment["id"] for deployment in list_deployments["deployments"]
        ]

        single_deployment = integration_client.apps.get_deployment(
            app_id, deployment_id
        )

        assert deployment_id == single_deployment["deployment"]["id"]

        # Deployment logs are not available until the deployment is complete.
        # Sleep until the build is finished. 😴
        time.sleep(120)

        agg_logs = integration_client.apps.get_logs_aggregate(
            app_id, deployment_id, type="BUILD"
        )

        assert agg_logs is not None

        logs = integration_client.apps.get_logs(
            app_id, deployment_id, "component", type="BUILD"
        )

        assert logs is not None

        cancel_deployment = integration_client.apps.cancel_deployment(
            app_id, deployment_id
        )

        assert deployment_id == cancel_deployment["deployment"]["id"]
