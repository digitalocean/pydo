# pylint: disable=duplicate-code
# pylint: disable=line-too-long
"""Mock tests for the app API resource."""
import responses

from digitalocean import Client


@responses.activate
def test_create(mock_client: Client, mock_client_url):
    "Mock Creating an App"
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
    """Test list of Apps"""
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
    """Mock Update an App"""
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
        responses.PUT,
        f"{mock_client_url}/v2/apps/4f6c71e2-1e90-4762-9fee-6cc4a0a9f2cf",
        json=expected,
        status=200,
    )

    update_resp = mock_client.apps.update(
        "4f6c71e2-1e90-4762-9fee-6cc4a0a9f2cf",
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
                "services": [],
                "static_sites": [
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
                    }
                ],
                "jobs": [
                    {
                        "name": "api",
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
        },
    )
    assert update_resp == expected


@responses.activate
def test_delete(mock_client: Client, mock_client_url):
    """Mock Delete App"""
    expected = {"id": "1"}
    responses.add(
        responses.DELETE, f"{mock_client_url}/v2/apps/1", json=expected, status=200
    )

    del_resp = mock_client.apps.delete(1)

    assert del_resp == expected


@responses.activate
def test_propose(mock_client: Client, mock_client_url):
    """Mock Propose App"""
    expected = {
        "app_name_available": True,
        "existing_static_apps": "2",
        "max_free_static_apps": "3",
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
                    "instance_count": 1,
                    "http_port": 8080,
                    "routes": [{"path": "/"}],
                }
            ],
            "region": "ams",
        },
        "app_cost": 5,
        "app_tier_upgrade_cost": 17,
    }

    responses.add(
        responses.POST, f"{mock_client_url}/v2/apps/propose", json=expected, status=200
    )

    proposed_spec = {
        "spec": {
            "name": "web-app",
            "region": "nyc",
            "services": [
                {
                    "name": "api",
                    "github": {
                        "branch": "main",
                        "deploy_on_push": True,
                        "repo": "digitalocean/sample-golang",
                    },
                    "run_command": "bin/api",
                    "environment_slug": "node-js",
                    "instance_count": 2,
                    "instance_size_slug": "basic-xxs",
                    "routes": [{"path": "/api"}],
                }
            ],
        },
        "app_id": "b6bdf840-2854-4f87-a36c-5f231c617c84",
    }

    propose_resp = mock_client.apps.validate_app_spec(proposed_spec)

    assert propose_resp == expected


@responses.activate
def test_list_alerts(mock_client: Client, mock_client_url):
    """Mock list alerts"""

    expected = {
        "alerts": [
            {
                "id": "e552e1f9-c1b0-4e6d-8777-ad6f27767306",
                "spec": {"rule": "DEPLOYMENT_FAILED"},
                "emails": ["sammy@digitalocean.com"],
                "phase": "ACTIVE",
                "progress": {
                    "steps": [
                        {
                            "name": "alert-configure-insight-alert",
                            "status": "SUCCESS",
                            "started_at": "2020-07-28T18:00:00Z",
                            "ended_at": "2020-07-28T18:00:00Z",
                        }
                    ]
                },
            },
            {
                "id": "b58cc9d4-0702-4ffd-ab45-4c2a8d979527",
                "spec": {
                    "rule": "CPU_UTILIZATION",
                    "operator": "GREATER_THAN",
                    "value": 85,
                    "window": "FIVE_MINUTES",
                },
                "emails": ["sammy@digitalocean.com"],
                "phase": "ACTIVE",
                "progress": {
                    "steps": [
                        {
                            "name": "alert-configure-insight-alert",
                            "status": "SUCCESS",
                            "started_at": "2020-07-28T18:00:00Z",
                            "ended_at": "2020-07-28T18:00:00Z",
                        }
                    ]
                },
            },
        ]
    }
    responses.add(
        responses.GET, f"{mock_client_url}/v2/apps/1/alerts", json=expected, status=200
    )

    list_resp = mock_client.apps.list_alerts("1")

    assert list_resp == expected


@responses.activate
def test_tiers(mock_client: Client, mock_client_url):
    """Tests list Tiers"""
    expected = {
        "tiers": [
            {
                "name": "Starter",
                "slug": "starter",
                "egress_bandwidth_bytes": "1073741824",
                "build_seconds": "6000",
            },
            {
                "name": "Basic",
                "slug": "basic",
                "egress_bandwidth_bytes": "42949672960",
                "build_seconds": "24000",
            },
            {
                "name": "Professional",
                "slug": "professional",
                "egress_bandwidth_bytes": "107374182400",
                "build_seconds": "60000",
            },
        ]
    }

    responses.add(
        responses.GET, f"{mock_client_url}/v2/apps/tiers", json=expected, status=200
    )

    list_resp = mock_client.apps.list_tiers()

    assert list_resp == expected


@responses.activate
def test_change_alerts(mock_client: Client, mock_client_url):
    """Test Change Alerts"""

    expected = {
        "alert": {
            "id": "e552e1f9-c1b0-4e6d-8777-ad6f27767306",
            "spec": {"rule": "DEPLOYMENT_FAILED"},
            "emails": ["sammy@digitalocean.com"],
            "phase": "ACTIVE",
            "progress": {
                "steps": [
                    {
                        "name": "alert-configure-insight-alert",
                        "status": "SUCCESS",
                        "started_at": "2020-07-28T18:00:00Z",
                        "ended_at": "2020-07-28T18:00:00Z",
                    }
                ]
            },
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/apps/1/alerts/2/destinations",
        json=expected,
        status=200,
    )

    req = {
        "emails": ["sammy@digitalocean.com"],
        "slack_webhooks": [
            {
                "url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
                "channel": "Channel Name",
            }
        ],
    }

    post_resp = mock_client.apps.assign_alert_destinations("1", "2", req)

    assert post_resp == expected


@responses.activate
def test_tier(mock_client: Client, mock_client_url):
    """Tests Get Tier"""
    expected = {
        "tier": {
            "name": "Basic",
            "slug": "basic",
            "egress_bandwidth_bytes": "42949672960",
            "build_seconds": "24000",
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/apps/tiers/basic",
        json=expected,
        status=200,
    )
    get_resp = mock_client.apps.get_tier("basic")

    assert get_resp == expected


@responses.activate
def test_instances(mock_client: Client, mock_client_url):
    """Tests Get Instances"""
    expected = {
        "instance_sizes": [
            {
                "name": "Basic XXS",
                "slug": "basic-xxs",
                "cpu_type": "SHARED",
                "cpus": "1",
                "memory_bytes": "536870912",
                "usd_per_month": "5.00",
                "usd_per_second": "0.000002066799",
                "tier_slug": "basic",
                "tier_upgrade_to": "professional-xs",
            },
            {
                "name": "Basic XS",
                "slug": "basic-xs",
                "cpu_type": "SHARED",
                "cpus": "1",
                "memory_bytes": "1073741824",
                "usd_per_month": "10.00",
                "usd_per_second": "0.000004133598",
                "tier_slug": "basic",
                "tier_upgrade_to": "professional-xs",
            },
            {
                "name": "Basic S",
                "slug": "basic-s",
                "cpu_type": "SHARED",
                "cpus": "1",
                "memory_bytes": "2147483648",
                "usd_per_month": "20.00",
                "usd_per_second": "0.000008267196",
                "tier_slug": "basic",
                "tier_upgrade_to": "professional-s",
            },
            {
                "name": "Basic M",
                "slug": "basic-m",
                "cpu_type": "SHARED",
                "cpus": "2",
                "memory_bytes": "4294967296",
                "usd_per_month": "40.00",
                "usd_per_second": "0.000016534392",
                "tier_slug": "basic",
                "tier_upgrade_to": "professional-m",
            },
            {
                "name": "Professional XS",
                "slug": "professional-xs",
                "cpu_type": "SHARED",
                "cpus": "1",
                "memory_bytes": "1073741824",
                "usd_per_month": "12.00",
                "usd_per_second": "0.000004960317",
                "tier_slug": "professional",
                "tier_downgrade_to": "basic-xs",
            },
            {
                "name": "Professional S",
                "slug": "professional-s",
                "cpu_type": "SHARED",
                "cpus": "1",
                "memory_bytes": "2147483648",
                "usd_per_month": "25.00",
                "usd_per_second": "0.000010333995",
                "tier_slug": "professional",
                "tier_downgrade_to": "basic-s",
            },
            {
                "name": "Professional M",
                "slug": "professional-m",
                "cpu_type": "SHARED",
                "cpus": "2",
                "memory_bytes": "4294967296",
                "usd_per_month": "50.00",
                "usd_per_second": "0.000020667989",
                "tier_slug": "professional",
                "tier_downgrade_to": "basic-s",
            },
            {
                "name": "Professional 1L",
                "slug": "professional-1l",
                "cpu_type": "DEDICATED",
                "cpus": "1",
                "memory_bytes": "4294967296",
                "usd_per_month": "75.00",
                "usd_per_second": "0.000031001984",
                "tier_slug": "professional",
                "tier_downgrade_to": "basic-m",
            },
            {
                "name": "Professional L",
                "slug": "professional-l",
                "cpu_type": "DEDICATED",
                "cpus": "2",
                "memory_bytes": "8589934592",
                "usd_per_month": "150.00",
                "usd_per_second": "0.000062003968",
                "tier_slug": "professional",
                "tier_downgrade_to": "basic-s",
            },
            {
                "name": "Professional XL",
                "slug": "professional-xl",
                "cpu_type": "DEDICATED",
                "cpus": "4",
                "memory_bytes": "17179869184",
                "usd_per_month": "300.00",
                "usd_per_second": "0.000124007937",
                "tier_slug": "professional",
                "tier_downgrade_to": "basic-s",
            },
        ]
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/apps/tiers/instance_sizes",
        json=expected,
        status=200,
    )

    list_resp = mock_client.apps.list_instance_sizes()

    assert list_resp == expected


@responses.activate
def test_instance(mock_client: Client, mock_client_url):
    """Test Get Instance"""

    expected = {
        "instance_size": {
            "name": "Basic XXS",
            "slug": "basic-xxs",
            "cpu_type": "SHARED",
            "cpus": "1",
            "memory_bytes": "536870912",
            "usd_per_month": "5.00",
            "usd_per_second": "0.000002066799",
            "tier_slug": "basic",
            "tier_upgrade_to": "professional-xs",
        }
    }
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/apps/tiers/instance_sizes/basic-xxs",
        json=expected,
        status=200,
    )
    get_resp = mock_client.apps.get_instance_size("basic-xxs")

    assert get_resp == expected


@responses.activate
def test_regions(mock_client: Client, mock_client_url):
    """Test Get Regions"""

    expected = {
        "regions": [
            {
                "slug": "ams",
                "label": "Amsterdam",
                "flag": "netherlands",
                "continent": "Europe",
                "data_centers": ["ams3"],
            },
            {
                "slug": "nyc",
                "label": "New York",
                "flag": "usa",
                "continent": "North America",
                "data_centers": ["nyc1", "nyc3"],
                "default": True,
            },
            {
                "slug": "fra",
                "label": "Frankfurt",
                "flag": "germany",
                "continent": "Europe",
                "data_centers": ["fra1"],
            },
            {
                "slug": "sfo",
                "label": "San Francisco",
                "flag": "usa",
                "continent": "North America",
                "data_centers": ["sfo3"],
            },
            {
                "slug": "sgp",
                "label": "Singapore",
                "flag": "singapore",
                "continent": "Asia",
                "data_centers": ["sgp1"],
            },
            {
                "slug": "blr",
                "label": "Bangalore",
                "flag": "india",
                "continent": "Asia",
                "data_centers": ["blr1"],
            },
            {
                "slug": "tor",
                "label": "Toronto",
                "flag": "canada",
                "continent": "North America",
                "data_centers": ["tor1"],
            },
            {
                "slug": "lon",
                "label": "London",
                "flag": "uk",
                "continent": "Europe",
                "data_centers": ["lon1"],
            },
        ]
    }

    responses.add(
        responses.GET, f"{mock_client_url}/v2/apps/regions", json=expected, status=200
    )

    list_resp = mock_client.apps.list_regions()

    assert list_resp == expected
