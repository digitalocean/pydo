""" test_cdn.py
    Integration tests for CDN
"""

from tests.integration import shared
from digitalocean import Client


def test_cdn_lifecycle(integration_client: Client, spaces_endpoint: str):
    """Tests the complete lifecycle of a CDN
    Creates, Lists, Gets, Updates, Deletes, Purges.
    """

    cdn_req = {"origin": spaces_endpoint, "ttl": 3600}

    with shared.with_test_cdn(integration_client, cdn_req) as cdn:
        cdn_id = cdn["endpoint"]["id"]

        list_resp = integration_client.cdn.list_endpoints()

        assert cdn_id in [endpoints["id"] for endpoints in list_resp["endpoints"]]

        get_resp = integration_client.cdn.get_endpoint(cdn_id)

        assert cdn_id == get_resp["endpoint"]["id"]

        ttl = 86400
        update_req = {"ttl": ttl}

        update_resp = integration_client.cdn.update_endpoints(cdn_id, update_req)

        assert update_resp["endpoints"]["ttl"] == ttl

        purge_req = {"files": ["*"]}

        purge_resp = integration_client.cdn.purge_cache(cdn_id, purge_req)

        assert purge_resp is None
