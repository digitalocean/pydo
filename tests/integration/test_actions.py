""" test_actions.py
    Integration Test for Domains
"""

from digitalocean import DigitalOceanClient


def test_actions(integration_client: DigitalOceanClient):
    """Testing the List and Gets
    of the actions endpoint
    """

    list_resp = integration_client.actions.list()

    assert list_resp is not None

    action_id = list_resp["actions"][0]["id"] or 0

    assert action_id is not 0

    get_resp = integration_client.actions.get(action_id)

    assert action_id == get_resp["action"]["id"]
