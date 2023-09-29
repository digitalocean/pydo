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
def test_databases_delete(mock_client: Client, mock_client_url):
    """Mocks the databases delete operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"
    database_name = 'alpha'

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/dbs/{database_name}",
        status = 204,
    )

    resp = mock_client.databases.delete(cluster_uuid, database_name)

    assert resp is None 


@responses.activate
def test_databases_delete_connection_pool(mock_client: Client, mock_client_url):
    """Mocks the databases delete connection pool operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    pool_name = 'backend-pool'

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/pools/{pool_name}",
        status = 204,
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
        status = 204,
    )

    resp = mock_client.databases.delete_online_migration(cluster_uuid,migration_id)

    assert resp is None


@responses.activate
def test_databases_delete_user(mock_client: Client, mock_client_url):
    """Mocks the databases delete user operation."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    user_name = 'app-01'

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/users/{user_name}",
        status = 204,
    )
    
    resp = mock_client.databases.delete_user(cluster_uuid,user_name)
    
    assert resp is None


@responses.activate
def test_databases_destroy_replica(mock_client: Client, mock_client_url):
    """Mocks the databases destroy replica operation that destroy a read only replica."""

    cluster_uuid = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    replica_name = 'read_nyc_3'
    
    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/databases/{cluster_uuid}/replicas/{replica_name}",
        status = 204,
    )
    
    resp = mock_client.databases.destroy_replica(cluster_uuid,replica_name)

    assert resp is None
