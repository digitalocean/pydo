# pylint: disable=line-too-long

"""Mock tests for the Monitoring API resource."""
import responses

from pydo import Client


@responses.activate
def test_monitoring_list(mock_client: Client, mock_client_url):
    """Mocks the Monitoring List Alert Policies"""

    expected = {
        "policies": [
            {
                "alerts": {
                    "email": ["bob@example.com"],
                    "slack": [
                        {
                            "channel": "Production Alerts",
                            "url": 'https://hooks.slack.com/services/T1234567/AAAAAAAA/ZZZZZZ"',
                        }
                    ],
                },
                "compare": "GreaterThan",
                "description": "CPU Alert",
                "enabled": True,
                "entities": [192018292],
                "tags": ["production_droplets"],
                "type": "v1/insights/droplet/cpu",
                "uuid": "78b3da62-27e5-49ba-ac70-5db0b5935c64",
                "value": 80,
                "window": "5m",
            }
        ],
        "links": {
            "first": "https//api.digitalocean.com/v2/monitoring/alerts?page=1&per_page=10",
            "prev": "https//api.digitalocean.com/v2/monitoring/alerts?page=2&per_page=10",
            "next": "https//api.digitalocean.com/v2/monitoring/alerts?page=4&per_page=10",
            "last": "https//api.digitalocean.com/v2/monitoring/alerts?page=5&per_page=10",
        },
        "meta": {"total": 50},
    }
    responses.add(
        responses.GET, f"{mock_client_url}/v2/monitoring/alerts", json=expected
    )

    list_resp = mock_client.monitoring.list_alert_policy()
    assert list_resp == expected


@responses.activate
def test_monitoring_create(mock_client: Client, mock_client_url):
    """Tests Projects Creation"""
    expected = {
        "alerts": {
            "email": ["bob@exmaple.com"],
            "slack": [
                {
                    "channel": "Production Alerts",
                    "url": "https://hooks.slack.com/services/T1234567/AAAAAAAA/ZZZZZZ",
                }
            ],
        },
        "compare": "GreaterThan",
        "description": "CPU Alert",
        "enabled": True,
        "entities": ["192018292"],
        "tags": ["droplet_tag"],
        "type": "v1/insights/droplet/cpu",
        "uuid": "78b3da62-27e5-49ba-ac70-5db0b5935c64",
        "value": 80,
        "window": "5m",
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/monitoring/alerts",
        json=expected,
        status=200,
    )

    create_resp = mock_client.monitoring.create_alert_policy(
        body={
            "alerts": {
                "email": ["bob@exmaple.com"],
                "slack": [
                    {
                        "channel": "Production Alerts",
                        "url": "https://hooks.slack.com/services/T1234567/AAAAAAAA/ZZZZZZ",
                    }
                ],
            },
            "compare": "GreaterThan",
            "description": "CPU Alert",
            "enabled": True,
            "entities": ["192018292"],
            "tags": ["droplet_tag"],
            "type": "v1/insights/droplet/cpu",
            "value": 80,
            "window": "5m",
        }
    )

    assert create_resp == expected


@responses.activate
def test_monitoring_get(mock_client: Client, mock_client_url):
    """Test Monitoring Get Existing Alert Policy"""
    expected = {
        "alerts": {
            "email": ["bob@exmaple.com"],
            "slack": [
                {
                    "channel": "Production Alerts",
                    "url": "https://hooks.slack.com/services/T1234567/AAAAAAAA/ZZZZZZ",
                }
            ],
        },
        "compare": "GreaterThan",
        "description": "CPU Alert",
        "enabled": True,
        "entities": ["192018292"],
        "tags": ["droplet_tag"],
        "type": "v1/insights/droplet/cpu",
        "uuid": "78b3da62-27e5-49ba-ac70-5db0b5935c64",
        "value": 80,
        "window": "5m",
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/monitoring/alerts/78b3da62-27e5-49ba-ac70-5db0b5935c64",
        json=expected,
        status=200,
    )

    get_resp = mock_client.monitoring.get_alert_policy(
        alert_uuid="78b3da62-27e5-49ba-ac70-5db0b5935c64"
    )

    assert get_resp == expected


@responses.activate
def test_monitoring_update(mock_client: Client, mock_client_url):
    """Test Monitoring Update Existing Alert Policy"""
    expected = {
        "alerts": {
            "email": ["cart@exmaple.com"],
            "slack": [
                {
                    "channel": "Production Alerts",
                    "url": "https://hooks.slack.com/services/T1234567/AAAAAAAA/ZZZZZZ",
                }
            ],
        },
        "compare": "GreaterThan",
        "description": "CPU Alert",
        "enabled": True,
        "entities": ["192018292"],
        "tags": ["droplet_tag"],
        "type": "v1/insights/droplet/cpu",
        "uuid": "78b3da62-27e5-49ba-ac70-5db0b5935c64",
        "value": 80,
        "window": "5m",
    }

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/monitoring/alerts/78b3da62-27e5-49ba-ac70-5db0b5935c64",
        json=expected,
        status=200,
    )

    update_resp = mock_client.monitoring.update_alert_policy(
        alert_uuid="78b3da62-27e5-49ba-ac70-5db0b5935c64",
        body={
            "alerts": {
                "email": ["cart@exmaple.com"],
                "slack": [
                    {
                        "channel": "Production Alerts",
                        "url": "https://hooks.slack.com/services/T1234567/AAAAAAAA/ZZZZZZ",
                    }
                ],
            },
            "compare": "GreaterThan",
            "description": "CPU Alert",
            "enabled": True,
            "entities": ["192018292"],
            "tags": ["droplet_tag"],
            "type": "v1/insights/droplet/cpu",
            "uuid": "78b3da62-27e5-49ba-ac70-5db0b5935c64",
            "value": 80,
            "window": "5m",
        },
    )

    assert update_resp == expected


@responses.activate
def test_monitoring_delete(mock_client: Client, mock_client_url):
    """Test Monitoring Delete"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/monitoring/alerts/4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
        status=204,
    )
    del_resp = mock_client.monitoring.delete_alert_policy(
        alert_uuid="4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679"
    )

    assert del_resp is None


@responses.activate
def test_monitoring_get_droplet_bandwidth(mock_client: Client, mock_client_url):
    """Test Monitoring Get Droplet Bandwith Metric"""
    expected = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {
                        "direction": "inbound",
                        "host_id": "222651441",
                        "interface": "private",
                    },
                    "values": [
                        [1634052360, "0.016600450090265357"],
                        [1634052480, "0.015085955677299055"],
                        [1634052600, "0.014941163855322308"],
                        [1634052720, "0.016214285714285712"],
                    ],
                }
            ],
        },
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/monitoring/metrics/droplet/bandwidth",
        json=expected,
        status=200,
    )

    get_resp = mock_client.monitoring.get_droplet_bandwidth_metrics(
        host_id="3124593",
        interface="public",
        direction="outbound",
        start="1620683817",
        end="1620705417",
    )

    assert get_resp == expected


@responses.activate
def test_monitoring_get_droplet_cpu(mock_client: Client, mock_client_url):
    """Test Monitoring Get Droplet CPU Metric"""
    expected = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"host_id": "222651441", "mode": "idle"},
                    "values": [
                        [1635386880, "122901.18"],
                        [1635387000, "123020.92"],
                        [1635387120, "123140.8"],
                    ],
                },
                {
                    "metric": {"host_id": "222651441", "mode": "iowait"},
                    "values": [
                        [1635386880, "14.99"],
                        [1635387000, "15.01"],
                        [1635387120, "15.01"],
                    ],
                },
                {
                    "metric": {"host_id": "222651441", "mode": "irq"},
                    "values": [[1635386880, "0"], [1635387000, "0"], [1635387120, "0"]],
                },
                {
                    "metric": {"host_id": "222651441", "mode": "nice"},
                    "values": [
                        [1635386880, "66.35"],
                        [1635387000, "66.35"],
                        [1635387120, "66.35"],
                    ],
                },
                {
                    "metric": {"host_id": "222651441", "mode": "softirq"},
                    "values": [
                        [1635386880, "2.13"],
                        [1635387000, "2.13"],
                        [1635387120, "2.13"],
                    ],
                },
                {
                    "metric": {"host_id": "222651441", "mode": "steal"},
                    "values": [
                        [1635386880, "7.89"],
                        [1635387000, "7.9"],
                        [1635387120, "7.91"],
                    ],
                },
                {
                    "metric": {"host_id": "222651441", "mode": "system"},
                    "values": [
                        [1635386880, "140.09"],
                        [1635387000, "140.2"],
                        [1635387120, "140.23"],
                    ],
                },
                {
                    "metric": {"host_id": "222651441", "mode": "user"},
                    "values": [
                        [1635386880, "278.57"],
                        [1635387000, "278.65"],
                        [1635387120, "278.69"],
                    ],
                },
            ],
        },
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/monitoring/metrics/droplet/cpu",
        json=expected,
        status=200,
    )

    get_resp = mock_client.monitoring.get_droplet_cpu_metrics(
        host_id="3124562", start="1620683817", end="1620705417"
    )

    assert get_resp == expected


@responses.activate
def test_monitoring_get_droplet_filesystem_free(mock_client: Client, mock_client_url):
    """Test Monitoring Get Droplet Filesystem Free Metrics"""
    expected = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {
                        "device": "/dev/vda1",
                        "fstype": "ext4",
                        "host_id": "222651441",
                        "mountpoint": "/",
                    },
                    "values": [
                        [1635386880, "25832407040"],
                        [1635387000, "25832407040"],
                        [1635387120, "25832407040"],
                    ],
                }
            ],
        },
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/monitoring/metrics/droplet/filesystem_free",
        json=expected,
        status=200,
    )

    get_resp = mock_client.monitoring.get_droplet_filesystem_free_metrics(
        host_id="3124562", start="1620683817", end="1620705417"
    )

    assert get_resp == expected


@responses.activate
def test_monitoring_get_droplet_filesystem_size(mock_client: Client, mock_client_url):
    """Test Monitoring Get Droplet Filesystem Size Metrics"""
    expected = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {
                        "device": "/dev/vda1",
                        "fstype": "ext4",
                        "host_id": "222651441",
                        "mountpoint": "/",
                    },
                    "values": [
                        [1635386880, "25832407040"],
                        [1635387000, "25832407040"],
                        [1635387120, "25832407040"],
                    ],
                }
            ],
        },
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/monitoring/metrics/droplet/filesystem_size",
        json=expected,
        status=200,
    )

    get_resp = mock_client.monitoring.get_droplet_filesystem_size_metrics(
        host_id="3124562", start="1620683817", end="1620705417"
    )

    assert get_resp == expected


@responses.activate
def test_monitoring_get_droplet_load1_metric(mock_client: Client, mock_client_url):
    """Test Monitoring Get Droplet Load1 Metrics"""
    expected = {
        "data": {
            "result": [
                {
                    "metric": {"host_id": "19201920"},
                    "values": [[1435781430, "1"], [1435781445, "1"]],
                }
            ],
            "resultType": "matrix",
        },
        "status": "success",
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/monitoring/metrics/droplet/load_1",
        json=expected,
        status=200,
    )

    get_resp = mock_client.monitoring.get_droplet_load1_metrics(
        host_id="3124562", start="1620683817", end="1620705417"
    )

    assert get_resp == expected


@responses.activate
def test_monitoring_get_droplet_load5_metric(mock_client: Client, mock_client_url):
    """Test Monitoring Get Droplet Load5 Metrics"""
    expected = {
        "data": {
            "result": [
                {
                    "metric": {"host_id": "19201920"},
                    "values": [[1435781430, "1"], [1435781445, "1"]],
                }
            ],
            "resultType": "matrix",
        },
        "status": "success",
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/monitoring/metrics/droplet/load_5",
        json=expected,
        status=200,
    )

    get_resp = mock_client.monitoring.get_droplet_load5_metrics(
        host_id="3124562", start="1620683817", end="1620705417"
    )

    assert get_resp == expected


@responses.activate
def test_monitoring_get_droplet_load15_metric(mock_client: Client, mock_client_url):
    """Test Monitoring Get Droplet Load15 Metrics"""
    expected = {
        "data": {
            "result": [
                {
                    "metric": {"host_id": "19201920"},
                    "values": [[1435781430, "1"], [1435781445, "1"]],
                }
            ],
            "resultType": "matrix",
        },
        "status": "success",
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/monitoring/metrics/droplet/load_15",
        json=expected,
        status=200,
    )

    get_resp = mock_client.monitoring.get_droplet_load15_metrics(
        host_id="3124562", start="1620683817", end="1620705417"
    )

    assert get_resp == expected


@responses.activate
def test_monitoring_get_droplet_cached_memory(mock_client: Client, mock_client_url):
    """Test Monitoring Get Droplet Cached Memory Metrics"""
    expected = {
        "data": {
            "result": [
                {
                    "metric": {"host_id": "19201920"},
                    "values": [[1435781430, "1"], [1435781445, "1"]],
                }
            ],
            "resultType": "matrix",
        },
        "status": "success",
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/monitoring/metrics/droplet/memory_cached",
        json=expected,
        status=200,
    )

    get_resp = mock_client.monitoring.get_droplet_memory_cached_metrics(
        host_id="3124562", start="1620683817", end="1620705417"
    )

    assert get_resp == expected


@responses.activate
def test_monitoring_get_droplet_free_memory(mock_client: Client, mock_client_url):
    """Test Monitoring Get Droplet Free Memory Metrics"""
    expected = {
        "data": {
            "result": [
                {
                    "metric": {"host_id": "19201920"},
                    "values": [[1435781430, "1"], [1435781445, "1"]],
                }
            ],
            "resultType": "matrix",
        },
        "status": "success",
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/monitoring/metrics/droplet/memory_free",
        json=expected,
        status=200,
    )

    get_resp = mock_client.monitoring.get_droplet_memory_free_metrics(
        host_id="3124562", start="1620683817", end="1620705417"
    )

    assert get_resp == expected


@responses.activate
def test_monitoring_get_droplet_total_memory(mock_client: Client, mock_client_url):
    """Test Monitoring Get Droplet Total Memory Metrics"""
    expected = {
        "data": {
            "result": [
                {
                    "metric": {"host_id": "19201920"},
                    "values": [[1435781430, "1"], [1435781445, "1"]],
                }
            ],
            "resultType": "matrix",
        },
        "status": "success",
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/monitoring/metrics/droplet/memory_total",
        json=expected,
        status=200,
    )

    get_resp = mock_client.monitoring.get_droplet_memory_total_metrics(
        host_id="3124562", start="1620683817", end="1620705417"
    )

    assert get_resp == expected


@responses.activate
def test_monitoring_get_droplet_available_memory(mock_client: Client, mock_client_url):
    """Test Monitoring Get Droplet Available Memory Metrics"""
    expected = {
        "data": {
            "result": [
                {
                    "metric": {"host_id": "19201920"},
                    "values": [[1435781430, "1"], [1435781445, "1"]],
                }
            ],
            "resultType": "matrix",
        },
        "status": "success",
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/monitoring/metrics/droplet/memory_available",
        json=expected,
        status=200,
    )

    get_resp = mock_client.monitoring.get_droplet_memory_available_metrics(
        host_id="3124562", start="1620683817", end="1620705417"
    )

    assert get_resp == expected
