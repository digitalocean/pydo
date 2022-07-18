""" test_domain.py
    Integration Test for Domains
"""

from tests.integration import defaults
from tests.integration import shared
from digitalocean import DigitalOceanClient


def test_domains_create_record(integration_client: DigitalOceanClient):
    """Testing the creation of a Domain.
    and creating a record from created domain.
    """
    name = f"{defaults.PREFIX}.com"
    create_domain = {"name": name}

    with shared.with_test_domain(integration_client, create_domain) as domain:
        list_resp = integration_client.domains.list()
        assert len(list_resp["domains"]) > 0

        get_resp = integration_client.domains.get(domain["domain"]["name"])
        assert name == get_resp["domain"]["name"]

        create_record = {
            "type": "A",
            "name": name,
            "data": "162.10.66.0",
            "priority": None,
            "port": None,
            "ttl": 1800,
            "weight": None,
            "flags": None,
            "tag": None,
        }

        with shared.with_test_domain_record(
            integration_client, name, create_record
        ) as record:
            list_resp = integration_client.domains.list_records(name)
            assert len(list_resp["domain_records"]) > 0

            record_id = record["domain_record"]["id"]
            get_resp = integration_client.domains.get_record(name, record_id)
            assert get_resp["domain_record"]["id"] == record_id

            ttl = 900
            patch_request = {"type": "A", "ttl": ttl}

            patch_resp = integration_client.domains.patch_record(
                name, record_id, patch_request
            )
            assert patch_resp["domain_record"]["ttl"] == ttl

            ttl = 1000
            update_request = {"type": "A", "ttl": ttl}

            update_resp = integration_client.domains.update_record(
                name, record_id, update_request
            )
            assert update_resp["domain_record"]["ttl"] == ttl
