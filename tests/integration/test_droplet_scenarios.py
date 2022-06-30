import uuid

from azure.core.exceptions import HttpResponseError

import defaults
import shared
from digitalocean import DigitalOceanClient


def test_droplet_attach_volume(integration_client: DigitalOceanClient, ssh_key):
    droplet_req = {
        "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
        "region": defaults.REGION,
        "size": defaults.DROPLET_SIZE,
        "image": defaults.DROPLET_IMAGE,
        "ssh_keys": [ssh_key]
    }

    with shared.with_test_droplet(integration_client, **droplet_req) as d:
        # TODO: look into implement polling
        # (https://github.com/Azure/autorest.python/blob/autorestv3/docs/generate/directives.md#generate-with-a-custom-poller)
        shared.wait_for_action(integration_client, d['links']['actions'][0]['id'])
        droplet_get_resp = integration_client.droplets.get(d['droplet']['id'])
        assert droplet_get_resp['droplet']['status'] == 'active'

        volume_req = {
            "size_gigabytes": 10,
            "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
            "description": "Block storage testing",
            "region": defaults.REGION,
            "filesystem_type": "ext4",
        }

        with shared.with_test_volume(integration_client, **volume_req) as v:

            attach_req = {
                "type": "attach",
                "droplet_id": d['droplet']['id']
            }

            try:
                vol_attach_resp = integration_client.volume_actions.post_by_id(v['volume']['id'], attach_req)
            except HttpResponseError as err:
                assert False, f"unexpected HttpResponseError: {err.message}"

            shared.wait_for_action(integration_client, vol_attach_resp['action']['id'])
            droplet_get_resp = integration_client.droplets.get(d['droplet']['id'])
            assert vol_attach_resp['volume']['id'] in droplet_get_resp['droplet']['volume_ids']
