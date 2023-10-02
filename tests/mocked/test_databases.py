# pylint: disable=line-too-long
"""Mock tests for the databases API resource."""

import responses

from pydo import Client


@responses.activate
def test_databases_add(mock_client: Client, mock_client_url):
    """Mocks the databases add database operation."""

    expected = {"db": {"name": "alpha"}}

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/dbs",
        json=expected,
        status=201,
    )

    resp = mock_client.databases.add(cluster_uuid, {"name": "alpha"})

    assert expected == resp


@responses.activate
def test_databases_add_connection_pool(mock_client: Client, mock_client_url):
    """Mocks the databases add connection pool operation."""

    expected = {
        "pool": {
            "user": "doadmin",
            "name": "backend-pool",
            "size": 10,
            "db": "defaultdb",
            "mode": "transaction",
            "connection": {
                "uri": "postgres://doadmin:wv78n3zpz42xezdk@backend-do-user-19081923-0.db.ondigitalocean.com:25061/backend-pool?sslmode=require",
                "database": "backend-pool",
                "host": "backend-do-user-19081923-0.db.ondigitalocean.com",
                "port": 25061,
                "user": "doadmin",
                "password": "wv78n3zpz42xezdk",
                "ssl": True,
            },
        }
    }

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/pools",
        json=expected,
        status=201,
    )

    resp = mock_client.databases.add_connection_pool(
        cluster_uuid,
        {
            "name": "backend-pool",
            "mode": "transaction",
            "size": 10,
            "db": "defaultdb",
            "user": "doadmin",
        },
    )

    assert expected == resp


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
def test_databases_create_cluster(mock_client: Client, mock_client_url):
    """Mocks the databases create cluster operation."""

    expected = {
        "database": {
            "id": "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30",
            "name": "backend-cluster",
            "engine": "pg",
            "version": "14",
            "semantic_version": "14.5",
            "connection": {
                "uri": "postgres://doadmin:wv78n3zpz42xezdk@backend-do-user-19081923-0.db.ondigitalocean.com:25060/defaultdb?sslmode=require",
                "database": "",
                "host": "backend-do-user-19081923-0.db.ondigitalocean.com",
                "port": 25060,
                "user": "doadmin",
                "password": "wv78n3zpz42xezdk",
                "ssl": True,
            },
            "private_connection": {
                "uri": "postgres://doadmin:wv78n3zpz42xezdk@private-backend-do-user-19081923-0.db.ondigitalocean.com:25060/defaultdb?sslmode=require",
                "database": "",
                "host": "private-backend-do-user-19081923-0.db.ondigitalocean.com",
                "port": 25060,
                "user": "doadmin",
                "password": "wv78n3zpz42xezdk",
                "ssl": True,
            },
            "users": [
                {"name": "doadmin", "role": "primary", "password": "wv78n3zpz42xezdk"}
            ],
            "db_names": ["defaultdb"],
            "num_nodes": 3,
            "region": "nyc3",
            "status": "creating",
            "created_at": "2019-01-11T18:37:36Z",
            "maintenance_window": {
                "day": "saturday",
                "hour": "08:45:12",
                "pending": True,
                "description": [
                    "Update TimescaleDB to version 1.2.1",
                    "Upgrade to PostgreSQL 11.2 and 10.7 bugfix releases",
                ],
            },
            "size": "db-s-2vcpu-4gb",
            "tags": ["production"],
            "private_network_uuid": "d455e75d-4858-4eec-8c95-da2f0a5f93a7",
            "version_end_of_life": "2023-11-09T00:00:00Z",
            "version_end_of_availability": "2023-05-09T00:00:00Z",
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/databases",
        json=expected,
        status=201,
    )

    resp = mock_client.databases.create_cluster(
        {
            "name": "backend-cluster",
            "engine": "pg",
            "version": "14",
            "region": "nyc3",
            "size": "db-s-2vcpu-4gb",
            "num_nodes": 3,
            "tags": ["production"],
        }
    )

    assert expected == resp


@responses.activate
def test_databases_add_user(mock_client: Client, mock_client_url):
    """Mocks the databases add user operation."""

    expected = {
        "user": {"name": "app-01", "role": "normal", "password": "jge5lfxtzhx42iff"}
    }
    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/users",
        json=expected,
        status=201,
    )

    resp = mock_client.databases.add_user(cluster_uuid, {"name": "app-01"})

    assert expected == resp


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
def test_databases_create_replica(mock_client: Client, mock_client_url):
    """Mocks the databases create replica operation."""

    expected = {
        "replica": {
            "name": "read-nyc3-01",
            "connection": {
                "uri": "",
                "database": "defaultdb",
                "host": "read-nyc3-01-do-user-19081923-0.db.ondigitalocean.com",
                "port": 25060,
                "user": "doadmin",
                "password": "wv78n3zpz42xezdk",
                "ssl": True,
            },
            "private_connection": {
                "uri": "postgres://doadmin:wv78n3zpz42xezdk@private-read-nyc3-01-do-user-19081923-0.db.ondigitalocean.com:25060/defaultdb?sslmode=require",
                "database": "",
                "host": "private-read-nyc3-01-do-user-19081923-0.db.ondigitalocean.com",
                "port": 25060,
                "user": "doadmin",
                "password": "wv78n3zpz42xezdk",
                "ssl": True,
            },
            "region": "nyc3",
            "status": "online",
            "created_at": "2019-01-11T18:37:36Z",
        }
    }

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/replicas",
        json=expected,
        status=201,
    )

    resp = mock_client.databases.create_replica(
        cluster_uuid,
        {"name": "read-nyc3-01", "region": "nyc3", "size": "db-s-2vcpu-4gb"},
    )

    assert expected == resp


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
def test_databases_delete(mock_client: Client, mock_client_url):
    """Mocks the databases delete operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"
    database_name = "alpha"

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/dbs/{database_name}",
        status=204,
    )

    resp = mock_client.databases.delete(cluster_uuid, database_name)

    assert resp is None


@responses.activate
def test_databases_delete_connection_pool(mock_client: Client, mock_client_url):
    """Mocks the databases delete connection pool operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    pool_name = "backend-pool"

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/pools/{pool_name}",
        status=204,
    )

    resp = mock_client.databases.delete_connection_pool(cluster_uuid, pool_name)

    assert resp is None


@responses.activate
def test_databases_delete_online_migration(mock_client: Client, mock_client_url):
    """Mocks the databases delete online migration operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    migration_id = "77b28fc8-19ff-11eb-8c9c-c68e24557488"

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/online-migration/{migration_id}",
        status=204,
    )

    resp = mock_client.databases.delete_online_migration(cluster_uuid, migration_id)

    assert resp is None


@responses.activate
def test_databases_delete_user(mock_client: Client, mock_client_url):
    """Mocks the databases delete user operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    user_name = "app-01"

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/users/{user_name}",
        status=204,
    )

    resp = mock_client.databases.delete_user(cluster_uuid, user_name)

    assert resp is None


@responses.activate
def test_databases_destroy_replica(mock_client: Client, mock_client_url):
    """Mocks the databases destroy replica operation that destroy a read only replica."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    replica_name = "read_nyc_3"

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/replicas/{replica_name}",
        status=204,
    )

    resp = mock_client.databases.destroy_replica(cluster_uuid, replica_name)

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
