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

    resp = mock_client.databases.promote_replica(
        cluster_uuid, replica_name
    )

    assert resp is None
