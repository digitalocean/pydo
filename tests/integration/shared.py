import contextlib
import typing
from time import sleep

from azure.core.exceptions import HttpResponseError

from digitalocean import DigitalOceanClient


class IntegrationTestError(Exception):
    pass


def wait_for_action(client: DigitalOceanClient, action_id: int, wait_seconds: int = 5):
    # TODO: look into implement polling
    # (https://github.com/Azure/autorest.python/blob/autorestv3/docs/generate/directives.md#generate-with-a-custom-poller)
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


def wait_for_kubernetes_cluster_create(client: DigitalOceanClient, cluster_id: str, wait_seconds: int = 15):
    # TODO: look into implement polling
    # (https://github.com/Azure/autorest.python/blob/autorestv3/docs/generate/directives.md#generate-with-a-custom-poller)
    while True:
        try:
            resp = client.kubernetes.get_cluster(cluster_id)
            state = resp['kubernetes_cluster']['status']['state']
        except HttpResponseError as err:
            raise IntegrationTestError(f"Error: {err.status_code} {err.reason}: {err.error.message}")
        else:
            state = resp['kubernetes_cluster']['status']['state']
            if state == "running":
                break
            elif state == "error":
                raise Exception(f"Cluster {cluster_id} error status: {resp['kubernetes_cluster']['status']['state']}")
        sleep(wait_seconds)


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


@contextlib.contextmanager
def with_test_kubernetes_cluster(client: DigitalOceanClient, **kwargs):
    create_resp = client.kubernetes.create_cluster(kwargs)
    kubernetes_cluster = create_resp['kubernetes_cluster']['id'] or ''
    assert kubernetes_cluster != ''
    try:
        yield create_resp
    finally:
        client.kubernetes.delete_cluster(kubernetes_cluster)
