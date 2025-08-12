"""Mock tests for the keys API resource."""

import responses
from responses import matchers

from pydo import Client


@responses.activate
def test_list_ssh_keys(mock_client: Client, mock_client_url):
    """Tests the SSH keys list operation."""
    expected = {
        "ssh_keys": [
            {
                "id": 1234,
                "public_key": "ssh-rsa aaaBBBccc123 key",
                "name": "key",
                "fingerprint": "17:23:a1:4f:55:4b:59:c6:ad:f7:69:dc:4e:85:e4:8a",
            },
            {
                "id": 5678,
                "public_key": "ssh-rsa longKeyString test",
                "name": "test",
                "fingerprint": "0a:56:d2:46:64:64:12:95:34:ce:e7:vf:0f:c8:5a:d3",
            },
        ],
        "links": {"pages": {}},
        "meta": {"total": 2},
    }

    responses.add(responses.GET, f"{mock_client_url}/v2/account/keys", json=expected)
    keys = mock_client.ssh_keys.list()

    assert keys == expected


@responses.activate
def test_list_ssh_keys_pagination(mock_client: Client, mock_client_url):
    """Tests the SSH keys list operation."""
    expected = {
        "ssh_keys": [
            {
                "id": 1234,
                "public_key": "ssh-rsa aaaBBBccc123 key",
                "name": "key",
                "fingerprint": "17:23:a1:4f:55:4b:59:c6:ad:f7:69:dc:4e:85:e4:8a",
            },
            {
                "id": 5678,
                "public_key": "ssh-rsa longKeyString test",
                "name": "test",
                "fingerprint": "0a:56:d2:46:64:64:12:95:34:ce:e7:vf:0f:c8:5a:d3",
            },
        ],
        "links": {
            "pages": {
                "next": "https://api.digitalocean.com/v2/account/keys?page=2",
                "last": "https://api.digitalocean.com/v2/account/keys?page=3",
            }
        },
        "meta": {"total": 6},
    }

    params = {"per_page": 2, "page": 2}
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/account/keys",
        json=expected,
        match=[matchers.query_param_matcher(params)],
    )
    keys = mock_client.ssh_keys.list(per_page=2, page=2)

    assert keys == expected


@responses.activate
def test_get_ssh_keys(mock_client: Client, mock_client_url):
    """Tests the SSH keys get operation."""
    expected = {
        "ssh_key": {
            "id": 1234,
            "public_key": "ssh-rsa aaaBBBccc123 key",
            "name": "key",
            "fingerprint": "17:23:a1:4f:55:4b:59:c6:ad:f7:69:dc:4e:85:e4:8a",
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/account/keys/1234",
        json=expected,
    )
    keys = mock_client.ssh_keys.get(ssh_key_identifier=1234)

    assert keys == expected


@responses.activate
def test_create_ssh_keys(mock_client: Client, mock_client_url):
    """Tests the SSH keys create operation."""
    expected = {
        "ssh_key": {
            "id": 1234,
            "public_key": "ssh-rsa aaaBBBccc123 key",
            "name": "key",
            "fingerprint": "17:23:a1:4f:55:4b:59:c6:ad:f7:69:dc:4e:85:e4:8a",
        }
    }

    responses.add(
        responses.POST, f"{mock_client_url}/v2/account/keys", json=expected, status=201
    )
    keys = mock_client.ssh_keys.create(
        {"name": "key", "public_key": "ssh-rsa aaaBBBccc123 key"}
    )

    assert keys == expected


@responses.activate
def test_update_ssh_keys(mock_client: Client, mock_client_url):
    """Tests the SSH keys create operation."""
    expected = {
        "ssh_key": {
            "id": 1234,
            "public_key": "ssh-rsa aaaBBBccc123 key",
            "name": "new-name",
            "fingerprint": "17:23:a1:4f:55:4b:59:c6:ad:f7:69:dc:4e:85:e4:8a",
        }
    }

    responses.add(
        responses.PUT, f"{mock_client_url}/v2/account/keys/1234", json=expected
    )
    keys = mock_client.ssh_keys.update(
        ssh_key_identifier=1234, body={"name": "new-name"}
    )

    assert keys == expected


@responses.activate
def test_delete_ssh_keys(mock_client: Client, mock_client_url):
    """Tests the SSH keys delete operation."""
    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/account/keys/1234",
        status=204,
    )

    mock_client.ssh_keys.delete(ssh_key_identifier=1234)


@responses.activate
def test_ssh_keys_error_response(mock_client: Client, mock_client_url):
    """Tests the SSH keys error response."""
    expected = {
        "id": "not_found",
        "message": "The resource you requested could not be found.",
    }

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/account/keys/1234",
        json=expected,
        status=404,
    )

    error = mock_client.ssh_keys.delete(ssh_key_identifier=1234)

    assert error == expected
