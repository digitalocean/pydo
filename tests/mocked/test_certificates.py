"""Mock tests for the certificates API resource"""

import responses

from digitalocean import Client


@responses.activate
def test_certificates_create(mock_client: Client, mock_client_url):
    """Tests Certificates Creation"""
    expected = {
        "certificate": {
            "id": "892071a0-bb95-49bc-8021-3afd67a210bf",
            "name": "web-cert-01",
            "not_after": "2017-02-22T00:23:00Z",
            "sha1_fingerprint": "dfcc9f57d86bf58e321c2c6c31c7a971be244ac7",
            "created_at": "2017-02-08T16:02:37Z",
            "dns_names": [""],
            "state": "verified",
            "type": "custom",
        }
    }
    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/certificates",
        json=expected,
        status=201,
    )

    create_resp = mock_client.certificates.create(
        {
            "name": "web-cert-01",
            "type": "lets_encrypt",
            "dns_names": ["www.example.com", "example.com"],
        }
    )

    assert create_resp == expected


@responses.activate
def test_certificates_get(mock_client: Client, mock_client_url):
    """Test Get Existing Certificate"""
    expected = {
        "certificate": {
            "id": "892071a0-bb95-49bc-8021-3afd67a210bf",
            "name": "web-cert-01",
            "not_after": "2017-02-22T00:23:00Z",
            "sha1_fingerprint": "dfcc9f57d86bf58e321c2c6c31c7a971be244ac7",
            "created_at": "2017-02-08T16:02:37Z",
            "dns_names": [""],
            "state": "verified",
            "type": "custom",
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/certificates/892071a0-bb95-49bc-8021-3afd67a210bf",
        json=expected,
        status=200,
    )

    get_resp = mock_client.certificates.get(
        certificate_id="892071a0-bb95-49bc-8021-3afd67a210bf"
    )

    assert get_resp == expected


@responses.activate
def test_certificates_list(mock_client: Client, mock_client_url):
    """Test Certificates List"""
    expected = {
        "certificates": [
            {
                "id": "892071a0-bb95-49bc-8021-3afd67a210bf",
                "name": "web-cert-01",
                "not_after": "2017-02-22T00:23:00Z",
                "sha1_fingerprint": "dfcc9f57d86bf58e321c2c6c31c7a971be244ac7",
                "created_at": "2017-02-08T16:02:37Z",
                "dns_names": [""],
                "state": "verified",
                "type": "custom",
            },
            {
                "id": "ba9b9c18-6c59-46c2-99df-70da170a42ba",
                "name": "web-cert-02",
                "not_after": "2018-06-07T17:44:12Z",
                "sha1_fingerprint": "479c82b5c63cb6d3e6fac4624d58a33b267e166c",
                "created_at": "2018-03-09T18:44:11Z",
                "dns_names": ["www.example.com", "example.com"],
                "state": "verified",
                "type": "lets_encrypt",
            },
        ],
        "links": {},
        "meta": {"total": 2},
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/certificates",
        json=expected,
        status=200,
    )

    list_resp = mock_client.certificates.list()

    assert list_resp == expected


@responses.activate
def test_certificates_delete(mock_client: Client, mock_client_url):
    """Test Certificates Delete"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/certificates/892071a0-bb95-49bc-8021-3afd67a210bf",
        status=204,
    )
    del_resp = mock_client.certificates.delete(
        certificate_id="892071a0-bb95-49bc-8021-3afd67a210bf"
    )

    assert del_resp is None
