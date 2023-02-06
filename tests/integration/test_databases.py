""" test_databases.py
    Integration Test for Databases
"""

import uuid

import pytest
from pydo import Client
from tests.integration import defaults, shared


@pytest.mark.long_running
def test_databases_update_connection_pool(integration_client: Client):
    """Tests updating the connection pool for a database (PostgreSQL).

    Creates a database cluster and waits for its status to be `active`.
    Then creates a connection pool.
    Then updates the connection pool.
    The cluster gets deleted when complete.
    """

    db_create_req = {
        "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
        "engine": "pg",
        "version": "14",
        "region": "nyc3",
        "size": "db-s-2vcpu-4gb",
        "num_nodes": 2,
        "tags": ["production"],
    }

    with shared.with_test_database(
        integration_client, wait=True, **db_create_req
    ) as database_resp:
        db_id = database_resp["database"]["id"]

        create_pool_req = {
            "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
            "mode": "transaction",
            "size": 10,
            "db": "defaultdb",
            "user": "doadmin",
        }

        pool_resp = integration_client.databases.add_connection_pool(
            db_id, create_pool_req
        )

        assert pool_resp is not None
        assert "pool" in pool_resp.keys()
        pool_name = pool_resp["pool"]["name"]

        new_pool_mode = "session"
        new_pool_size = 15

        update_pool_resp = integration_client.databases.update_connection_pool(
            db_id,
            pool_name,
            {
                "mode": new_pool_mode,
                "size": new_pool_size,
                "db": "defaultdb",
                "user": "doadmin",
            },
        )

        assert update_pool_resp is None

        pool_details = integration_client.databases.get_connection_pool(
            db_id, pool_name
        )

        assert pool_details["pool"]["mode"] == new_pool_mode
        assert pool_details["pool"]["size"] == new_pool_size


@pytest.mark.long_running
def test_databases_update_major_version(integration_client: Client):
    """Tests updating the databases version.

    Creates a database cluster and waits for its status to be `active`.
    Then updates the cluster.
    """

    db_create_req = {
        "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
        "engine": "pg",
        "version": "13",
        "region": "nyc3",
        "size": "db-s-2vcpu-4gb",
        "num_nodes": 2,
        "tags": ["production"],
    }

    with shared.with_test_database(
        integration_client, wait=True, **db_create_req
    ) as database_resp:
        db_id = database_resp["database"]["id"]

        update_req = {
            "version": "14",
        }

        update_resp = integration_client.databases.update_major_version(
            db_id, update_req
        )

        assert update_resp is None


@pytest.mark.long_running
def test_databases_create_replica_and_promote_as_primary(integration_client: Client):
    """Tests creating a replica of a database and promoting the
    replica as the primary database.
    """

    db_create_req = {
        "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
        "engine": "pg",
        "version": "13",
        "region": "nyc3",
        "size": "db-s-2vcpu-4gb",
        "num_nodes": 2,
        "tags": ["production"],
    }

    with shared.with_test_database(
        integration_client, wait=True, **db_create_req
    ) as database_resp:
        db_id = database_resp["database"]["id"]
        replica_name = "read-nyc3-01"

        create_replica = {
            "name": replica_name,
            "region": "nyc3",
            "size": "db-s-2vcpu-4gb",
        }

        create_rep_response = integration_client.databases.create_replica(
            db_id, create_replica
        )

        assert create_rep_response is not None

        promote_replica = integration_client.databases.promote_replica(
            db_id, replica_name
        )

        assert promote_replica is None
