"""Test client customizations like pagination helper."""

import pytest
import responses
from pydo import Client


@responses.activate
def test_pagination_helper(mock_client: Client, mock_client_url):
    """Test the pagination helper method."""

    # Mock multiple pages of SSH keys
    page1_data = {
        "ssh_keys": [
            {"id": 1, "name": "key1", "fingerprint": "fp1"},
            {"id": 2, "name": "key2", "fingerprint": "fp2"}
        ],
        "links": {
            "pages": {
                "next": f"{mock_client_url}/v2/account/keys?page=2&per_page=2"
            }
        },
        "meta": {"total": 4}
    }

    page2_data = {
        "ssh_keys": [
            {"id": 3, "name": "key3", "fingerprint": "fp3"},
            {"id": 4, "name": "key4", "fingerprint": "fp4"}
        ],
        "links": {
            "pages": {}
        },
        "meta": {"total": 4}
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/account/keys",
        json=page1_data,
        match=[responses.matchers.query_param_matcher({"page": "1", "per_page": "2"})],
    )

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/account/keys",
        json=page2_data,
        match=[responses.matchers.query_param_matcher({"page": "2", "per_page": "2"})],
    )

    # Test pagination
    keys = list(mock_client.paginate(mock_client.ssh_keys.list, per_page=2))

    assert len(keys) == 4
    assert keys[0]["name"] == "key1"
    assert keys[1]["name"] == "key2"
    assert keys[2]["name"] == "key3"
    assert keys[3]["name"] == "key4"


@responses.activate
def test_pagination_helper_single_page(mock_client: Client, mock_client_url):
    """Test pagination helper with single page of results."""

    page_data = {
        "ssh_keys": [
            {"id": 1, "name": "key1", "fingerprint": "fp1"}
        ],
        "links": {
            "pages": {}
        },
        "meta": {"total": 1}
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/account/keys",
        json=page_data,
        match=[responses.matchers.query_param_matcher({"page": "1", "per_page": "20"})],
    )

    # Test pagination with single page
    keys = list(mock_client.paginate(mock_client.ssh_keys.list))

    assert len(keys) == 1
    assert keys[0]["name"] == "key1"
