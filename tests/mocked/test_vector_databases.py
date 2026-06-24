# pylint: disable=line-too-long
# pylint: disable=too-many-lines
"""Mock tests for the vector_databases API resource."""

import responses

from pydo import Client


@responses.activate
def test_vector_databases_list(mock_client: Client, mock_client_url):
    """Mocks the vector_databases list operation."""

    expected = {
        "total": 1,
        "vector_dbs": [
            {
                "id": "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30",
                "name": "my-vector-db",
                "region": "tor1",
                "status": "active",
                "size": "small",
                "config": {
                    "default_quantization": "rq",
                    "enable_auto_schema": True,
                    "weaviate_version": "1.25.0",
                },
                "endpoints": {
                    "grpc": "my-db-tor1-a1b2c3d4-grpc.weaviate.ondigitalocean.com:443",
                    "http": "https://my-db-tor1-a1b2c3d4.weaviate.ondigitalocean.com",
                },
                "tags": ["production"],
                "project_id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
                "created_at": "2020-02-20T00:00:00Z",
                "updated_at": "2020-02-20T00:00:00Z",
            }
        ],
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/vector-databases",
        json=expected,
        status=200,
    )

    resp = mock_client.vector_databases.list()

    assert expected == resp


@responses.activate
def test_vector_databases_create(mock_client: Client, mock_client_url):
    """Mocks the vector_databases create operation."""

    expected = {
        "vector_db": {
            "id": "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30",
            "name": "my-vector-db",
            "region": "tor1",
            "status": "creating",
            "size": "small",
            "config": {
                "default_quantization": "rq",
                "enable_auto_schema": True,
                "weaviate_version": "1.25.0",
            },
            "endpoints": {
                "grpc": "my-db-tor1-a1b2c3d4-grpc.weaviate.ondigitalocean.com:443",
                "http": "https://my-db-tor1-a1b2c3d4.weaviate.ondigitalocean.com",
            },
            "tags": ["production"],
            "project_id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
            "created_at": "2020-02-20T00:00:00Z",
            "updated_at": "2020-02-20T00:00:00Z",
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/vector-databases",
        json=expected,
        status=201,
    )

    resp = mock_client.vector_databases.create(
        {
            "name": "my-vector-db",
            "project_id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
            "region": "tor1",
            "size": "small",
            "tags": ["production"],
        }
    )

    assert expected == resp


@responses.activate
def test_vector_databases_get(mock_client: Client, mock_client_url):
    """Mocks the vector_databases get operation."""

    expected = {
        "vector_db": {
            "id": "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30",
            "name": "my-vector-db",
            "region": "tor1",
            "status": "active",
            "size": "small",
            "config": {
                "default_quantization": "rq",
                "enable_auto_schema": True,
                "weaviate_version": "1.25.0",
            },
            "endpoints": {
                "grpc": "my-db-tor1-a1b2c3d4-grpc.weaviate.ondigitalocean.com:443",
                "http": "https://my-db-tor1-a1b2c3d4.weaviate.ondigitalocean.com",
            },
            "tags": ["production"],
            "project_id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
            "created_at": "2020-02-20T00:00:00Z",
            "updated_at": "2020-02-20T00:00:00Z",
        }
    }

    database_id = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/vector-databases/{database_id}",
        json=expected,
        status=200,
    )

    resp = mock_client.vector_databases.get(database_id)

    assert expected == resp


@responses.activate
def test_vector_databases_update(mock_client: Client, mock_client_url):
    """Mocks the vector_databases update operation."""

    expected = {
        "vector_db": {
            "id": "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30",
            "name": "my-vector-db",
            "region": "tor1",
            "status": "active",
            "size": "small",
            "config": {
                "default_quantization": "pq",
                "enable_auto_schema": False,
                "weaviate_version": "1.25.0",
            },
            "endpoints": {
                "grpc": "my-db-tor1-a1b2c3d4-grpc.weaviate.ondigitalocean.com:443",
                "http": "https://my-db-tor1-a1b2c3d4.weaviate.ondigitalocean.com",
            },
            "tags": ["production"],
            "project_id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
            "created_at": "2020-02-20T00:00:00Z",
            "updated_at": "2020-02-20T00:00:00Z",
        }
    }

    database_id = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/vector-databases/{database_id}",
        json=expected,
        status=200,
    )

    resp = mock_client.vector_databases.update(
        database_id,
        {
            "config": {
                "default_quantization": "pq",
                "enable_auto_schema": False,
            }
        },
    )

    assert expected == resp


@responses.activate
def test_vector_databases_delete(mock_client: Client, mock_client_url):
    """Mocks the vector_databases delete operation."""

    database_id = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/vector-databases/{database_id}",
        status=204,
    )

    resp = mock_client.vector_databases.delete(database_id)

    assert resp is None


@responses.activate
def test_vector_databases_list_backups(mock_client: Client, mock_client_url):
    """Mocks the vector_databases list backups operation."""

    expected = {
        "backups": [
            {
                "backup_id": "vectordb-9cc10173-e9ea-4176-9dbc-a4cee4c4ff30-20240101-120000",
                "completed_at": "2020-02-20T00:00:00Z",
                "started_at": "2020-02-20T00:00:00Z",
                "status": "SUCCESS",
            }
        ]
    }

    database_id = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/vector-databases/{database_id}/backups",
        json=expected,
        status=200,
    )

    resp = mock_client.vector_databases.list_backups(database_id)

    assert expected == resp


@responses.activate
def test_vector_databases_get_restore_status(mock_client: Client, mock_client_url):
    """Mocks the vector_databases get restore status operation."""

    expected = {
        "backup_id": "vectordb-9cc10173-e9ea-4176-9dbc-a4cee4c4ff30-20240101-120000",
        "error": "",
        "status": "SUCCESS",
    }

    database_id = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"
    backup_id = "vectordb-9cc10173-e9ea-4176-9dbc-a4cee4c4ff30-20240101-120000"

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/vector-databases/{database_id}/backups/{backup_id}/restore",
        json=expected,
        status=200,
    )

    resp = mock_client.vector_databases.get_restore_status(database_id, backup_id)

    assert expected == resp


@responses.activate
def test_vector_databases_post_restore_backup(mock_client: Client, mock_client_url):
    """Mocks the vector_databases restore from backup operation."""

    expected = {
        "backup_id": "vectordb-9cc10173-e9ea-4176-9dbc-a4cee4c4ff30-20240101-120000",
        "status": "STARTED",
    }

    database_id = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"
    backup_id = "vectordb-9cc10173-e9ea-4176-9dbc-a4cee4c4ff30-20240101-120000"

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/vector-databases/{database_id}/backups/{backup_id}/restore",
        json=expected,
        status=200,
    )

    resp = mock_client.vector_databases.post_restore_backup(
        database_id,
        backup_id,
        {"backup_id": backup_id, "id": database_id},
    )

    assert expected == resp


@responses.activate
def test_vector_databases_get_credentials(mock_client: Client, mock_client_url):
    """Mocks the vector_databases get credentials operation."""

    expected = {
        "api_token": "fake-api-token-for-testing",
        "user_id": "doadmin",
    }

    database_id = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/vector-databases/{database_id}/credentials",
        json=expected,
        status=200,
    )

    resp = mock_client.vector_databases.get_credentials(database_id)

    assert expected == resp


@responses.activate
def test_vector_databases_post_resize(mock_client: Client, mock_client_url):
    """Mocks the vector_databases resize operation."""

    expected = {
        "vector_db": {
            "id": "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30",
            "name": "my-vector-db",
            "region": "tor1",
            "status": "active",
            "size": "medium",
            "config": {
                "default_quantization": "rq",
                "enable_auto_schema": True,
                "weaviate_version": "1.25.0",
            },
            "endpoints": {
                "grpc": "my-db-tor1-a1b2c3d4-grpc.weaviate.ondigitalocean.com:443",
                "http": "https://my-db-tor1-a1b2c3d4.weaviate.ondigitalocean.com",
            },
            "tags": ["production"],
            "project_id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
            "created_at": "2020-02-20T00:00:00Z",
            "updated_at": "2020-02-20T00:00:00Z",
        }
    }

    database_id = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/vector-databases/{database_id}/resize",
        json=expected,
        status=200,
    )

    resp = mock_client.vector_databases.post_resize(
        database_id,
        {"id": database_id, "size": "medium"},
    )

    assert expected == resp


@responses.activate
def test_vector_databases_update_tags(mock_client: Client, mock_client_url):
    """Mocks the vector_databases update tags operation."""

    expected = {
        "vector_db": {
            "id": "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30",
            "name": "my-vector-db",
            "region": "tor1",
            "status": "active",
            "size": "small",
            "config": {
                "default_quantization": "rq",
                "enable_auto_schema": True,
                "weaviate_version": "1.25.0",
            },
            "endpoints": {
                "grpc": "my-db-tor1-a1b2c3d4-grpc.weaviate.ondigitalocean.com:443",
                "http": "https://my-db-tor1-a1b2c3d4.weaviate.ondigitalocean.com",
            },
            "tags": ["staging", "backend"],
            "project_id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
            "created_at": "2020-02-20T00:00:00Z",
            "updated_at": "2020-02-20T00:00:00Z",
        }
    }

    database_id = "9cc10173-e9ea-4176-9dbc-a4cee4c4ff30"

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/vector-databases/{database_id}/tags",
        json=expected,
        status=200,
    )

    resp = mock_client.vector_databases.update_tags(
        database_id,
        {"id": database_id, "tags": ["staging", "backend"]},
    )

    assert expected == resp
