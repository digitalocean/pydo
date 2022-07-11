"""Pytest configuration for integration tests."""

import secrets
from os import environ

import pytest
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from tests.integration import defaults
from digitalocean import DigitalOceanClient


@pytest.fixture(scope="session")
def integration_client() -> DigitalOceanClient:
    """Instantiates a DigitalOceanClient for use with integration tests.

    The client requires the environment variable DO_TOKEN with a valid API
    token.

    *IMPORTANT*: Use of this client will create real resources on the
    account.
    """
    token = environ.get("DO_TOKEN", None)

    if token is None:
        pytest.fail("Expected environment variable DO_TOKEN")

    client = DigitalOceanClient(token)
    return client


@pytest.fixture(scope="session")
def ssh_key(integration_client) -> str:
    """Handles creating or retrieving an ssh_key on the live account."""

    key = rsa.generate_private_key(
        backend=crypto_default_backend(), public_exponent=65537, key_size=2048
    )

    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH, crypto_serialization.PublicFormat.OpenSSH
    )

    req = {
        "name": f"{defaults.PREFIX}-{secrets.token_hex(4)}",
        "public_key": public_key.decode(),
    }

    client = integration_client
    resp = client.ssh_keys.create(req)
    fingerprint = resp["ssh_key"]["fingerprint"]

    yield fingerprint

    client.ssh_keys.delete(fingerprint)
