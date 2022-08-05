"""Mock tests for the app API resource."""
from turtle import update
import responses

from digitalocean import Client


@responses.activate
def test_create(mock_client: Client, mock_client_url):
    expected = {
        "app": {
            "id": "c2a93513-8d9b-4223-9d61-5e7272c81cf5",
            "owner_uuid": "a4e16f25-cdd1-4483-b246-d77f283c9209",
            "spec": {},
            "default_ingress": "https://sample-golang-zyhgn.ondigitalocean.app",
            "created_at": "2021-02-10T16:45:14Z",
            "updated_at": "2021-02-10T17:06:56Z",
            "active_deployment": {},
            "last_deployment_created_at": "2021-02-10T17:05:30Z",
            "live_url": "https://sample-golang-zyhgn.ondigitalocean.app",
            "region": {},
            "tier_slug": "basic",
            "live_url_base": "https://sample-golang-zyhgn.ondigitalocean.app",
            "live_domain": "sample-golang-zyhgn.ondigitalocean.app",
        }
    }

    responses.add(
        responses.POST, f"{mock_client_url}/v2/apps", json=expected, status=200
    )
    create_resp = mock_client.apps.create(
        {
            "spec": {
                "name": "web-app",
                "region": "nyc",
                "services": [
                    {
                        "name": "api",
                        "github": {},
                        "run_command": "bin/api",
                        "environment_slug": "node-js",
                        "instance_count": 2,
                        "instance_size_slug": "basic-xxs",
                        "routes": [],
                    }
                ],
            }
        }
    )

    assert create_resp == expected


@responses.activate
def test_list(mock_client: Client, mock_client_url):
    expected = {
        "apps": [
            {
                "id": "4f6c71e2-1e90-4762-9fee-6cc4a0a9f2cf",
                "owner_uuid": "ff36cbc6fd350fe12577f5123133bb5ba01a2419",
                "spec": {},
                "default_ingress": "https://sample-php-iaj87.ondigitalocean.app",
                "created_at": "2020-11-19T20:27:18Z",
                "updated_at": "2020-12-01T00:42:16Z",
                "active_deployment": {},
                "cause": "app spec updated",
                "progress": {},
                "last_deployment_created_at": "2020-12-01T00:40:05Z",
                "live_url": "https://sample-php-iaj87.ondigitalocean.app",
                "region": {},
                "tier_slug": "basic",
                "live_url_base": "https://sample-php-iaj87.ondigitalocean.app",
                "live_domain": "sample-php-iaj87.ondigitalocean.app",
            }
        ],
        "links": {"pages": {}},
        "meta": {"total": 1},
    }

    responses.add(
        responses.GET, f"{mock_client_url}/v2/apps", json=expected, status=200
    )

    list_resp = mock_client.apps.list()

    assert list_resp == expected


@responses.activate
def test_update(mock_client: Client, mock_client_url):
    expected = {
        "app": {
            "id": "c2a93513-8d9b-4223-9d61-5e7272c81cf5",
            "owner_uuid": "a4e16f25-cdd1-4483-b246-d77f283c9209",
            "spec": {},
            "default_ingress": "https://sample-golang-zyhgn.ondigitalocean.app",
            "created_at": "2021-02-10T16:45:14Z",
            "updated_at": "2021-02-10T17:06:56Z",
            "active_deployment": {},
            "last_deployment_created_at": "2021-02-10T17:05:30Z",
            "live_url": "https://sample-golang-zyhgn.ondigitalocean.app",
            "region": {},
            "tier_slug": "basic",
            "live_url_base": "https://sample-golang-zyhgn.ondigitalocean.app",
            "live_domain": "sample-golang-zyhgn.ondigitalocean.app",
        }
    }

    responses.add(
        responses.PUT, f"{mock_client_url}/v2/apps", json=expected, status=200
    )

    update_resp = mock_client.apps.update(
        {
            "spec": {
                "name": "web-app-01",
                "region": "nyc",
                "domains": [
                    {
                        "domain": "app.example.com",
                        "type": "DEFAULT",
                        "wildcard": True,
                        "zone": "example.com",
                        "minimum_tls_version": "1.3",
                    }
                ],
                "services": [
                    {
                        "name": "api",
                        "git": {
                            "branch": "main",
                            "repo_clone_url": "https://github.com/digitalocean/sample-golang.git",
                        },
                        "github": {
                            "branch": "main",
                            "deploy_on_push": True,
                            "repo": "digitalocean/sample-golang",
                        },
                        "gitlab": {
                            "branch": "main",
                            "deploy_on_push": True,
                            "repo": "digitalocean/sample-golang",
                        },
                        "image": {
                            "registry": "registry.hub.docker.com",
                            "registry_type": "DOCR",
                            "repository": "origin/master",
                            "tag": "latest",
                        },
                        "dockerfile_path": "path/to/Dockerfile",
                        "build_command": "npm run build",
                        "run_command": "bin/api",
                        "source_dir": "path/to/dir",
                        "envs": [
                            {
                                "key": "BASE_URL",
                                "scope": "BUILD_TIME",
                                "type": "GENERAL",
                                "value": "http://example.com",
                            }
                        ],
                        "environment_slug": "node-js",
                        "log_destinations": {
                            "name": "my_log_destination",
                            "papertrail": {
                                "endpoint": "https://mypapertrailendpoint.com"
                            },
                            "datadog": {
                                "endpoint": "https://mydatadogendpoint.com",
                                "api_key": "abcdefghijklmnopqrstuvwxyz0123456789",
                            },
                            "logtail": {
                                "token": "abcdefghijklmnopqrstuvwxyz0123456789"
                            },
                        },
                        "instance_count": 2,
                        "instance_size_slug": "basic-xxs",
                        "cors": {
                            "allow_origins": [
                                {"exact": "https://www.example.com"},
                                {"regex": "^.*example.com"},
                            ],
                            "allow_methods": [
                                "GET",
                                "OPTIONS",
                                "POST",
                                "PUT",
                                "PATCH",
                                "DELETE",
                            ],
                            "allow_headers": ["Content-Type", "X-Custom-Header"],
                            "expose_headers": ["Content-Encoding", "X-Custom-Header"],
                            "max_age": "5h30m",
                            "allow_credentials": False,
                        },
                        "health_check": {
                            "failure_threshold": 2,
                            "port": 80,
                            "http_path": "/health",
                            "initial_delay_seconds": 30,
                            "period_seconds": 60,
                            "success_threshold": 3,
                            "timeout_seconds": 45,
                        },
                        "http_port": 3000,
                        "internal_ports": [80, 443],
                        "routes": [{"path": "/api", "preserve_path_prefix": True}],
                    }
                ],
                "static_sites": [
                    {
                        "name": "api",
                        "git": {
                            "branch": "main",
                            "repo_clone_url": "https://github.com/digitalocean/sample-golang.git",
                        },
                        "github": {
                            "branch": "main",
                            "deploy_on_push": True,
                            "repo": "digitalocean/sample-golang",
                        },
                        "gitlab": {
                            "branch": "main",
                            "deploy_on_push": True,
                            "repo": "digitalocean/sample-golang",
                        },
                        "image": {
                            "registry": "registry.hub.docker.com",
                            "registry_type": "DOCR",
                            "repository": "origin/master",
                            "tag": "latest",
                        },
                        "dockerfile_path": "path/to/Dockerfile",
                        "build_command": "npm run build",
                        "run_command": "bin/api",
                        "source_dir": "path/to/dir",
                        "envs": [
                            {
                                "key": "BASE_URL",
                                "scope": "BUILD_TIME",
                                "type": "GENERAL",
                                "value": "http://example.com",
                            }
                        ],
                        "environment_slug": "node-js",
                        "log_destinations": {
                            "name": "my_log_destination",
                            "papertrail": {
                                "endpoint": "https://mypapertrailendpoint.com"
                            },
                            "datadog": {
                                "endpoint": "https://mydatadogendpoint.com",
                                "api_key": "abcdefghijklmnopqrstuvwxyz0123456789",
                            },
                            "logtail": {
                                "token": "abcdefghijklmnopqrstuvwxyz0123456789"
                            },
                        },
                        "index_document": "main.html",
                        "error_document": "error.html",
                        "catchall_document": "index.html",
                        "output_dir": "dist/",
                        "cors": {
                            "allow_origins": [
                                {"exact": "https://www.example.com"},
                                {"regex": "^.*example.com"},
                            ],
                            "allow_methods": [
                                "GET",
                                "OPTIONS",
                                "POST",
                                "PUT",
                                "PATCH",
                                "DELETE",
                            ],
                            "allow_headers": ["Content-Type", "X-Custom-Header"],
                            "expose_headers": ["Content-Encoding", "X-Custom-Header"],
                            "max_age": "5h30m",
                            "allow_credentials": False,
                        },
                        "routes": [{"path": "/api", "preserve_path_prefix": True}],
                    }
                ],
                "jobs": [
                    {
                        "name": "api",
                        "git": {
                            "branch": "main",
                            "repo_clone_url": "https://github.com/digitalocean/sample-golang.git",
                        },
                        "github": {
                            "branch": "main",
                            "deploy_on_push": True,
                            "repo": "digitalocean/sample-golang",
                        },
                        "gitlab": {
                            "branch": "main",
                            "deploy_on_push": True,
                            "repo": "digitalocean/sample-golang",
                        },
                        "image": {
                            "registry": "registry.hub.docker.com",
                            "registry_type": "DOCR",
                            "repository": "origin/master",
                            "tag": "latest",
                        },
                        "dockerfile_path": "path/to/Dockerfile",
                        "build_command": "npm run build",
                        "run_command": "bin/api",
                        "source_dir": "path/to/dir",
                        "envs": [
                            {
                                "key": "BASE_URL",
                                "scope": "BUILD_TIME",
                                "type": "GENERAL",
                                "value": "http://example.com",
                            }
                        ],
                        "environment_slug": "node-js",
                        "log_destinations": {
                            "name": "my_log_destination",
                            "papertrail": {
                                "endpoint": "https://mypapertrailendpoint.com"
                            },
                            "datadog": {
                                "endpoint": "https://mydatadogendpoint.com",
                                "api_key": "abcdefghijklmnopqrstuvwxyz0123456789",
                            },
                            "logtail": {
                                "token": "abcdefghijklmnopqrstuvwxyz0123456789"
                            },
                        },
                        "instance_count": 2,
                        "instance_size_slug": "basic-xxs",
                        "kind": "PRE_DEPLOY",
                    }
                ],
                "workers": [
                    {
                        "name": "api",
                        "git": {
                            "branch": "main",
                            "repo_clone_url": "https://github.com/digitalocean/sample-golang.git",
                        },
                        "github": {
                            "branch": "main",
                            "deploy_on_push": True,
                            "repo": "digitalocean/sample-golang",
                        },
                        "gitlab": {
                            "branch": "main",
                            "deploy_on_push": True,
                            "repo": "digitalocean/sample-golang",
                        },
                        "image": {
                            "registry": "registry.hub.docker.com",
                            "registry_type": "DOCR",
                            "repository": "origin/master",
                            "tag": "latest",
                        },
                        "dockerfile_path": "path/to/Dockerfile",
                        "build_command": "npm run build",
                        "run_command": "bin/api",
                        "source_dir": "path/to/dir",
                        "envs": [
                            {
                                "key": "BASE_URL",
                                "scope": "BUILD_TIME",
                                "type": "GENERAL",
                                "value": "http://example.com",
                            }
                        ],
                        "environment_slug": "node-js",
                        "log_destinations": {
                            "name": "my_log_destination",
                            "papertrail": {
                                "endpoint": "https://mypapertrailendpoint.com"
                            },
                            "datadog": {
                                "endpoint": "https://mydatadogendpoint.com",
                                "api_key": "abcdefghijklmnopqrstuvwxyz0123456789",
                            },
                            "logtail": {
                                "token": "abcdefghijklmnopqrstuvwxyz0123456789"
                            },
                        },
                        "instance_count": 2,
                        "instance_size_slug": "basic-xxs",
                    }
                ],
                "functions": [
                    {
                        "cors": {
                            "allow_origins": [
                                {"exact": "https://www.example.com"},
                                {"regex": "^.*example.com"},
                            ],
                            "allow_methods": [
                                "GET",
                                "OPTIONS",
                                "POST",
                                "PUT",
                                "PATCH",
                                "DELETE",
                            ],
                            "allow_headers": ["Content-Type", "X-Custom-Header"],
                            "expose_headers": ["Content-Encoding", "X-Custom-Header"],
                            "max_age": "5h30m",
                            "allow_credentials": False,
                        },
                        "routes": [{"path": "/api", "preserve_path_prefix": True}],
                        "name": "api",
                        "source_dir": "path/to/dir",
                        "alerts": [
                            {
                                "rule": "CPU_UTILIZATION",
                                "disabled": False,
                                "operator": "GREATER_THAN",
                                "value": 2.32,
                                "window": "FIVE_MINUTES",
                            }
                        ],
                        "envs": [
                            {
                                "key": "BASE_URL",
                                "scope": "BUILD_TIME",
                                "type": "GENERAL",
                                "value": "http://example.com",
                            }
                        ],
                        "git": {
                            "branch": "main",
                            "repo_clone_url": "https://github.com/digitalocean/sample-golang.git",
                        },
                        "github": {
                            "branch": "main",
                            "deploy_on_push": True,
                            "repo": "digitalocean/sample-golang",
                        },
                        "gitlab": {
                            "branch": "main",
                            "deploy_on_push": True,
                            "repo": "digitalocean/sample-golang",
                        },
                        "log_destinations": {
                            "name": "my_log_destination",
                            "papertrail": {
                                "endpoint": "https://mypapertrailendpoint.com"
                            },
                            "datadog": {
                                "endpoint": "https://mydatadogendpoint.com",
                                "api_key": "abcdefghijklmnopqrstuvwxyz0123456789",
                            },
                            "logtail": {
                                "token": "abcdefghijklmnopqrstuvwxyz0123456789"
                            },
                        },
                    }
                ],
                "databases": [
                    {
                        "cluster_name": "cluster_name",
                        "db_name": "my_db",
                        "db_user": "superuser",
                        "engine": "PG",
                        "name": "prod-db",
                        "production": True,
                        "version": "12",
                    }
                ],
            }
        }
    )
    assert update_resp == expected
