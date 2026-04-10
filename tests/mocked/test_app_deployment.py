# pylint: disable=duplicate-code
# pylint: disable=line-too-long
"""Mock tests for the app API resource."""
import responses

from pydo import Client


@responses.activate
def test_create(mock_client: Client, mock_client_url):
    """Mock Create App Deploy"""
    app_id = "1"
    expected = {
        "deployment": {
            "id": app_id,
            "spec": {
                "name": "sample-golang",
                "services": [
                    {
                        "name": "web",
                        "github": {
                            "repo": "digitalocean/sample-golang",
                            "branch": "branch",
                        },
                        "run_command": "bin/sample-golang",
                        "environment_slug": "go",
                        "instance_size_slug": "basic-xxs",
                        "instance_count": 2,
                        "routes": [{"path": "/"}],
                    }
                ],
                "region": "ams",
            },
            "services": [
                {
                    "name": "web",
                    "source_commit_hash": "9a4df0b8e161e323bc3cdf1dc71878080fe144fa",
                }
            ],
            "phase_last_updated_at": "0001-01-01T00:00:00Z",
            "created_at": "2020-07-28T18:00:00Z",
            "updated_at": "2020-07-28T18:00:00Z",
            "cause": "commit 9a4df0b pushed to github/digitalocean/sample-golang",
            "progress": {
                "pending_steps": 6,
                "total_steps": 6,
                "steps": [
                    {
                        "name": "build",
                        "status": "PENDING",
                        "steps": [
                            {"name": "initialize", "status": "PENDING"},
                            {
                                "name": "components",
                                "status": "PENDING",
                                "steps": [
                                    {
                                        "name": "web",
                                        "status": "PENDING",
                                        "component_name": "web",
                                        "message_base": "Building service",
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "name": "deploy",
                        "status": "PENDING",
                        "steps": [
                            {"name": "initialize", "status": "PENDING"},
                            {
                                "name": "components",
                                "status": "PENDING",
                                "steps": [
                                    {
                                        "name": "web",
                                        "status": "PENDING",
                                        "steps": [
                                            {
                                                "name": "deploy",
                                                "status": "PENDING",
                                                "component_name": "web",
                                                "message_base": "Deploying service",
                                            },
                                            {
                                                "name": "wait",
                                                "status": "PENDING",
                                                "component_name": "web",
                                                "message_base": "Waiting for service",
                                            },
                                        ],
                                        "component_name": "web",
                                    }
                                ],
                            },
                            {"name": "finalize", "status": "PENDING"},
                        ],
                    },
                ],
            },
            "phase": "PENDING_BUILD",
            "tier_slug": "basic",
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/apps/{app_id}/deployments",
        json=expected,
        status=200,
    )

    create_resp = mock_client.apps.create_deployment(app_id, {"force_build": True})

    assert create_resp == expected


@responses.activate
def test_list(mock_client: Client, mock_client_url):
    """Test List App Deployment"""
    app_id = "1"

    expected = {
        "deployments": [
            {
                "id": "b6bdf840-2854-4f87-a36c-5f231c617c84",
                "spec": {
                    "name": "sample-golang",
                    "services": [
                        {
                            "name": "web",
                            "github": {
                                "repo": "digitalocean/sample-golang",
                                "branch": "branch",
                            },
                            "run_command": "bin/sample-golang",
                            "environment_slug": "go",
                            "instance_size_slug": "basic-xxs",
                            "instance_count": 2,
                            "routes": [{"path": "/"}],
                        }
                    ],
                    "region": "ams",
                },
                "services": [
                    {
                        "name": "web",
                        "source_commit_hash": "9a4df0b8e161e323bc3cdf1dc71878080fe144fa",
                    }
                ],
                "phase_last_updated_at": "0001-01-01T00:00:00Z",
                "created_at": "2020-07-28T18:00:00Z",
                "updated_at": "2020-07-28T18:00:00Z",
                "cause": "commit 9a4df0b pushed to github/digitalocean/sample-golang",
                "progress": {
                    "pending_steps": 6,
                    "total_steps": 6,
                    "steps": [
                        {
                            "name": "build",
                            "status": "PENDING",
                            "steps": [
                                {"name": "initialize", "status": "PENDING"},
                                {
                                    "name": "components",
                                    "status": "PENDING",
                                    "steps": [
                                        {
                                            "name": "web",
                                            "status": "PENDING",
                                            "component_name": "web",
                                            "message_base": "Building service",
                                        }
                                    ],
                                },
                            ],
                        },
                        {
                            "name": "deploy",
                            "status": "PENDING",
                            "steps": [
                                {"name": "initialize", "status": "PENDING"},
                                {
                                    "name": "components",
                                    "status": "PENDING",
                                    "steps": [
                                        {
                                            "name": "web",
                                            "status": "PENDING",
                                            "steps": [
                                                {
                                                    "name": "deploy",
                                                    "status": "PENDING",
                                                    "component_name": "web",
                                                    "message_base": "Deploying service",
                                                },
                                                {
                                                    "name": "wait",
                                                    "status": "PENDING",
                                                    "component_name": "web",
                                                    "message_base": "Waiting for service",
                                                },
                                            ],
                                            "component_name": "web",
                                        }
                                    ],
                                },
                                {"name": "finalize", "status": "PENDING"},
                            ],
                        },
                    ],
                },
                "phase": "PENDING_BUILD",
                "tier_slug": "basic",
            }
        ],
        "links": {"pages": {}},
        "meta": {"total": 1},
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/apps/{app_id}/deployments",
        json=expected,
        status=200,
    )

    list_resp = mock_client.apps.list_deployments(app_id)

    assert list_resp == expected


@responses.activate
def test_retrieve_deployment(mock_client: Client, mock_client_url):
    """Mock Retrieve App Deployment"""
    app_id = "1"

    expected = {
        "deployment": {
            "id": "b6bdf840-2854-4f87-a36c-5f231c617c84",
            "spec": {
                "name": "sample-golang",
                "services": [
                    {
                        "name": "web",
                        "github": {
                            "repo": "digitalocean/sample-golang",
                            "branch": "branch",
                        },
                        "run_command": "bin/sample-golang",
                        "environment_slug": "go",
                        "instance_size_slug": "basic-xxs",
                        "instance_count": 2,
                        "routes": [{"path": "/"}],
                    }
                ],
                "region": "ams",
            },
            "services": [
                {
                    "name": "web",
                    "source_commit_hash": "9a4df0b8e161e323bc3cdf1dc71878080fe144fa",
                }
            ],
            "phase_last_updated_at": "0001-01-01T00:00:00Z",
            "created_at": "2020-07-28T18:00:00Z",
            "updated_at": "2020-07-28T18:00:00Z",
            "cause": "commit 9a4df0b pushed to github/digitalocean/sample-golang",
            "progress": {
                "pending_steps": 6,
                "total_steps": 6,
                "steps": [
                    {
                        "name": "build",
                        "status": "PENDING",
                        "steps": [
                            {"name": "initialize", "status": "PENDING"},
                            {
                                "name": "components",
                                "status": "PENDING",
                                "steps": [
                                    {
                                        "name": "web",
                                        "status": "PENDING",
                                        "component_name": "web",
                                        "message_base": "Building service",
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "name": "deploy",
                        "status": "PENDING",
                        "steps": [
                            {"name": "initialize", "status": "PENDING"},
                            {
                                "name": "components",
                                "status": "PENDING",
                                "steps": [
                                    {
                                        "name": "web",
                                        "status": "PENDING",
                                        "steps": [
                                            {
                                                "name": "deploy",
                                                "status": "PENDING",
                                                "component_name": "web",
                                                "message_base": "Deploying service",
                                            },
                                            {
                                                "name": "wait",
                                                "status": "PENDING",
                                                "component_name": "web",
                                                "message_base": "Waiting for service",
                                            },
                                        ],
                                        "component_name": "web",
                                    }
                                ],
                            },
                            {"name": "finalize", "status": "PENDING"},
                        ],
                    },
                ],
            },
            "phase": "PENDING_BUILD",
            "tier_slug": "basic",
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/apps/{app_id}/deployments/2",
        json=expected,
        status=200,
    )

    retrieve_resp = mock_client.apps.get_deployment(app_id, "2")

    assert retrieve_resp == expected


@responses.activate
def test_cancel_deployment(mock_client: Client, mock_client_url):
    """Mock Cancel Deployment"""

    expected = {
        "deployment": {
            "id": "b6bdf840-2854-4f87-a36c-5f231c617c84",
            "spec": {
                "name": "sample-golang",
                "services": [
                    {
                        "name": "web",
                        "github": {
                            "repo": "digitalocean/sample-golang",
                            "branch": "branch",
                        },
                        "run_command": "bin/sample-golang",
                        "environment_slug": "go",
                        "instance_size_slug": "basic-xxs",
                        "instance_count": 2,
                        "routes": [{"path": "/"}],
                    }
                ],
                "region": "ams",
            },
            "services": [
                {
                    "name": "web",
                    "source_commit_hash": "9a4df0b8e161e323bc3cdf1dc71878080fe144fa",
                }
            ],
            "phase_last_updated_at": "0001-01-01T00:00:00Z",
            "created_at": "2020-07-28T18:00:00Z",
            "updated_at": "2020-07-28T18:00:00Z",
            "cause": "commit 9a4df0b pushed to github/digitalocean/sample-golang",
            "progress": {
                "pending_steps": 6,
                "total_steps": 6,
                "steps": [
                    {
                        "name": "build",
                        "status": "PENDING",
                        "steps": [
                            {"name": "initialize", "status": "PENDING"},
                            {
                                "name": "components",
                                "status": "PENDING",
                                "steps": [
                                    {
                                        "name": "web",
                                        "status": "PENDING",
                                        "component_name": "web",
                                        "message_base": "Building service",
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "name": "deploy",
                        "status": "PENDING",
                        "steps": [
                            {"name": "initialize", "status": "PENDING"},
                            {
                                "name": "components",
                                "status": "PENDING",
                                "steps": [
                                    {
                                        "name": "web",
                                        "status": "PENDING",
                                        "steps": [
                                            {
                                                "name": "deploy",
                                                "status": "PENDING",
                                                "component_name": "web",
                                                "message_base": "Deploying service",
                                            },
                                            {
                                                "name": "wait",
                                                "status": "PENDING",
                                                "component_name": "web",
                                                "message_base": "Waiting for service",
                                            },
                                        ],
                                        "component_name": "web",
                                    }
                                ],
                            },
                            {"name": "finalize", "status": "PENDING"},
                        ],
                    },
                ],
            },
            "phase": "PENDING_BUILD",
            "tier_slug": "basic",
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/apps/1/deployments/2/cancel",
        json=expected,
        status=200,
    )

    cancel_resp = mock_client.apps.cancel_deployment("1", "2")

    assert cancel_resp == expected


@responses.activate
def test_get_agg_deployment_logs(mock_client: Client, mock_client_url):
    """Mock Get Aggregate Deployment Logs"""

    expected = {
        "live_url": "https://logs-example/build.log",
        "url": "https://logs/build.log",
        "historic_logs": ["https://logs-example/archive/build.log"],
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/apps/1/deployments/2/logs",
        json=expected,
        status=200,
    )

    get_resp = mock_client.apps.get_logs_aggregate("1", "2")

    assert get_resp == expected


@responses.activate
def test_get_deployment_logs(mock_client: Client, mock_client_url):
    """Mock Get Deployment Logs"""

    expected = {
        "live_url": "https://logs-example/build.log",
        "url": "https://logs/build.log",
        "historic_logs": ["https://logs-example/archive/build.log"],
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/apps/1/deployments/2/components/component/logs",
        json=expected,
        status=200,
    )

    get_resp = mock_client.apps.get_logs("1", "2", "component")

    assert get_resp == expected
