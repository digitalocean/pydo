import contextlib
from time import sleep

from azure.core.exceptions import HttpResponseError

from digitalocean import DigitalOceanClient


class IntegrationTestError(Exception):
    pass


def wait_for_action(client: DigitalOceanClient, action_id: int, wait_seconds: int = 5):
    resp = client.actions.get(action_id)
    status = resp['action']['status']

    while status == "in-progress":
        try:
            resp = client.actions.get(action_id)
        except HttpResponseError as err:
            raise IntegrationTestError(f"Error: {err.status_code} {err.reason}: {err.error.message}")
        else:
            status = resp['action']['status']
            if status == "in-progress":
                sleep(wait_seconds)
            elif status == "errored":
                raise Exception(f"{resp['action']['type']} action {resp['action']['id']} {status}")


@contextlib.contextmanager
def with_test_droplet(client: DigitalOceanClient, **kwargs):
    create_resp = client.droplets.create(kwargs)
    droplet_id = create_resp['droplet']['id'] or ''
    assert droplet_id != ''
    try:
        yield create_resp
    finally:
        client.droplets.destroy_with_associated_resources_dangerous(droplet_id, x_dangerous=True)


@contextlib.contextmanager
def with_test_volume(client: DigitalOceanClient, **kwargs):
    create_resp = client.volumes.create(kwargs)
    volume_id = create_resp['volume']['id'] or ''
    assert volume_id != ''
    try:
        yield create_resp
    finally:
        client.volumes.delete(volume_id)
