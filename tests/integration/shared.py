""" shared.py
This shared module provides helpers for working with the API through the client.
"""
import contextlib
from time import sleep
import secrets

from azure.core.exceptions import HttpResponseError

from digitalocean import DigitalOceanClient
from tests.integration import defaults


class IntegrationTestError(Exception):
    """Integration test exception"""


def wait_for_action(client: DigitalOceanClient, action_id: int, wait_seconds: int = 5):
    """Helper function to poll for an action to complete."""

    # TODO: look into implement polling
    # pylint: disable=line-too-long
    # (https://github.com/Azure/autorest.python/blob/autorestv3/docs/generate/directives.md#generate-with-a-custom-poller)
    # pylint: enable=line-too-long
    resp = client.actions.get(action_id)
    status = resp["action"]["status"]

    while status == "in-progress":
        try:
            resp = client.actions.get(action_id)
        except HttpResponseError as err:
            raise IntegrationTestError(
                f"Error: {err.status_code} {err.reason}: {err.error.message}"
            ) from err
        else:
            status = resp["action"]["status"]
            if status == "in-progress":
                sleep(wait_seconds)
            elif status == "errored":
                raise Exception(
                    f"{resp['action']['type']} action {resp['action']['id']} {status}"
                )


def wait_for_kubernetes_cluster_create(
    client: DigitalOceanClient, cluster_id: str, wait_seconds: int = 15
):
    """Helper function to poll for a kubernetes cluster to be provisioned."""

    # TODO: look into implement polling
    # pylint: disable=line-too-long
    # (https://github.com/Azure/autorest.python/blob/autorestv3/docs/generate/directives.md#generate-with-a-custom-poller)
    # pylint: enable=line-too-long
    while True:
        try:
            resp = client.kubernetes.get_cluster(cluster_id)
            state = resp["kubernetes_cluster"]["status"]["state"]
        except HttpResponseError as err:
            raise IntegrationTestError(
                f"Error: {err.status_code} {err.reason}: {err.error.message}"
            ) from err
        else:
            state = resp["kubernetes_cluster"]["status"]["state"]
            if state == "running":
                break
            if state == "error":
                raise Exception(f"Cluster {cluster_id} error status: {state}")
        sleep(wait_seconds)


@contextlib.contextmanager
def with_test_droplet(client: DigitalOceanClient, public_key: bytes, **kwargs):
    """Context function to create a Droplet with an SSH key.

    It is not necessary to provide "ssh_keys" the request body. A key is
    generated, uploaded to the account, and added to the request.

    Droplet (and associated resources) is destroyed when the context ends.
    """
    with with_ssh_key(client, public_key) as key:
        kwargs.update({"ssh_keys": [key]})

        create_resp = client.droplets.create(kwargs)
        droplet_id = create_resp["droplet"]["id"] or ""
        assert droplet_id != ""
        try:
            yield create_resp
        finally:
            client.droplets.destroy_with_associated_resources_dangerous(
                droplet_id, x_dangerous=True
            )


@contextlib.contextmanager
def with_test_domain(client: DigitalOceanClient, create_domain):
    """Context function to create a Domain.

    Domain is destroyed after context ends
    """
    create_resp = client.domains.create(create_domain)
    domain_name = create_resp["domain"]["name"] or ""
    assert domain_name != ""
    try:
        yield create_resp
    finally:
        client.domains.delete(domain_name)


@contextlib.contextmanager
def with_test_domain_record(client: DigitalOceanClient, name, create_record):
    """Context function to create a Domain Record.

    Record is destroyed after context ends
    """
    create_resp = client.domains.create_record(name, create_record)
    record_id = create_resp["domain_record"]["id"] or 0
    assert record_id != 0
    try:
        yield create_resp
    finally:
        client.domains.delete_record(name, record_id)


@contextlib.contextmanager
def with_test_tag(client: DigitalOceanClient, **kwargs):
    """Context function to create a tag.

    The tag is destroyed when the context ends.
    """
    create_resp = client.tags.create(kwargs)
    tag_id = create_resp["tag"]["name"] or ""
    assert tag_id != ""
    try:
        yield create_resp
    finally:
        client.tags.delete(tag_id=tag_id)


@contextlib.contextmanager
def with_test_volume(client: DigitalOceanClient, **kwargs):
    """Context function to create a volume.

    Volume id deleted when the context ends.
    """
    create_resp = client.volumes.create(kwargs)
    volume_id = create_resp["volume"]["id"] or ""
    assert volume_id != ""
    try:
        yield create_resp
    finally:
        client.volumes.delete(volume_id)


@contextlib.contextmanager
def with_test_kubernetes_cluster(client: DigitalOceanClient, **kwargs):
    """Context function that creates a kubernetes cluster.

    The cluster is deleted once the context ends.
    """
    create_resp = client.kubernetes.create_cluster(kwargs)
    kubernetes_cluster = create_resp["kubernetes_cluster"]["id"] or ""
    assert kubernetes_cluster != ""
    try:
        yield create_resp
    finally:
        client.kubernetes.delete_cluster(kubernetes_cluster)


@contextlib.contextmanager
def with_ssh_key(client: DigitalOceanClient, public_key) -> str:
    """Handles creating an ssh_key on the live account.

    Yields the fingerprint of the key.
    """
    req = {
        "name": f"{defaults.PREFIX}-{secrets.token_hex(4)}",
        "public_key": public_key.decode(),
    }

    resp = client.ssh_keys.create(req)
    fingerprint = resp["ssh_key"]["fingerprint"]

    try:
        yield fingerprint
    finally:
        client.ssh_keys.delete(fingerprint)
