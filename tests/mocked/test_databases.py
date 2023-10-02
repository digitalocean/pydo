# pylint: disable=line-too-long
"""Mock tests for the databases API resource."""

import responses

from pydo import Client


@responses.activate
def test_databases_update_connection_pool(mock_client: Client, mock_client_url):
    """Mocks the databases update connection pool operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"
    pool_name = "test"

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/pools/{pool_name}",
        status=204,
    )

    resp = mock_client.databases.update_connection_pool(
        cluster_uuid,
        pool_name,
        {"mode": "transaction", "size": 10, "db": "defaultdb", "user": "doadmin"},
    )

    assert resp is None


@responses.activate
def test_databases_update_major_version(mock_client: Client, mock_client_url):
    """Mocks the databases update major version."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/upgrade",
        status=204,
    )

    resp = mock_client.databases.update_major_version(
        cluster_uuid,
        {"version": "14"},
    )

    assert resp is None


@responses.activate
def test_databases_promote_replica(mock_client: Client, mock_client_url):
    """Mocks the databases promote replica to primary cluster function."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"
    replica_name = "postgres_nyc_replica"

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/replicas/{replica_name}/promote",
        status=204,
    )

    resp = mock_client.databases.promote_replica(cluster_uuid, replica_name)

    assert resp is None


@responses.activate
def test_databases_patch_config(mock_client: Client, mock_client_url):
    """Mocks the databases patch config operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.PATCH,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/config",
        status=200,
    )

    resp = mock_client.databases.patch_config(cluster_uuid, {"config": {}})

    assert resp is None


@responses.activate
def test_databases_reset_auth(mock_client: Client, mock_client_url):
    """Mocks the databases patch config operation."""

    expected = {
        "user": {"name": "app-01", "role": "normal", "password": "jge5lfxtzhx42iff"}
    }
    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"
    user_name = "app-01"

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/users/{user_name}/reset_auth",
        json=expected,
        status=200,
    )

    resp = mock_client.databases.reset_auth(
        cluster_uuid,
        user_name,
        {"mysql_settings": {"auth_plugin": "caching_sha2_password"}},
    )

    assert expected == resp

    user_name = "app-02"
    expected = {
        "user": {
            "name": "app-02",
            "role": "normal",
            "password": "wv78n3zpz42xezdk",
            "mysql_settings": {"auth_plugin": "mysql_native_password"},
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/users/{user_name}/reset_auth",
        json=expected,
        status=200,
    )

    resp = mock_client.databases.reset_auth(
        cluster_uuid,
        user_name,
        {"mysql_settings": {"auth_plugin": "caching_sha2_password"}},
    )

    assert expected == resp


@responses.activate
def test_databases_update_cluster_size(mock_client: Client, mock_client_url):
    """Mocks the databases patch config operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/resize",
        status=202,
    )

    resp = mock_client.databases.update_cluster_size(
        cluster_uuid, {"size": "db-s-4vcpu-8gb", "num_nodes": 3}
    )

    assert resp is None


@responses.activate
def test_databases_update_firewall_rules(mock_client: Client, mock_client_url):
    """Mocks the databases update firewall rules operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/firewall",
        status=204,
    )

    resp = mock_client.databases.update_firewall_rules(
        cluster_uuid,
        {
            "rules": [
                {"type": "ip_addr", "value": "192.168.1.1"},
                {"type": "k8s", "value": "ff2a6c52-5a44-4b63-b99c-0e98e7a63d61"},
                {"type": "droplet", "value": "163973392"},
                {"type": "tag", "value": "backend"},
            ]
        },
    )

    assert resp is None


@responses.activate
def test_databases_update_maintenance_window(mock_client: Client, mock_client_url):
    """Mocks the databases update firewall rules operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/maintenance",
        status=204,
    )

    resp = mock_client.databases.update_maintenance_window(
        cluster_uuid, {"day": "tuesday", "hour": "14:00"}
    )

    assert resp is None


@responses.activate
def test_databases_update_online_migration(mock_client: Client, mock_client_url):
    """Mocks the databases update firewall rules operation."""

    expected = {
        "id": "77b28fc8-19ff-11eb-8c9c-c68e24557488",
        "status": "running",
        "created_at": "2020-10-29T15:57:38Z",
    }

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/online-migration",
        json=expected,
        status=200,
    )

    resp = mock_client.databases.update_online_migration(
        cluster_uuid,
        {
            "source": {
                "host": "source-do-user-6607903-0.b.db.ondigitalocean.com",
                "dbname": "defaultdb",
                "port": 25060,
                "username": "doadmin",
                "password": "paakjnfe10rsrsmf",
            },
            "disable_ssl": False,
        },
    )

    assert expected == resp


@responses.activate
def test_databases_update_region(mock_client: Client, mock_client_url):
    """Mocks the databases update firewall rules operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/migrate",
        status=202,
    )

    resp = mock_client.databases.update_region(cluster_uuid, {"region": "lon1"})

    assert resp is None


@responses.activate
def test_databases_update_sql_mode(mock_client: Client, mock_client_url):
    """Mocks the databases update firewall rules operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/sql_mode",
        status=204,
    )

    resp = mock_client.databases.update_sql_mode(
        cluster_uuid,
        {
            "sql_mode": "ANSI,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION,NO_ZERO_DATE,NO_ZERO_IN_DATE"
        },
    )

    assert resp is None
