"""Pytest configuration for integration tests."""

from os import environ

import pytest

from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from digitalocean import GeneratedClient


@pytest.fixture(scope="session")
def integration_client() -> GeneratedClient:
    """Instantiates a DigitalOceanClient for use with integration tests.

    The client requires the environment variable DO_TOKEN with a valid API
    token.

    *IMPORTANT*: Use of this client will create real resources on the
    account.
    """
    token = environ.get("DO_TOKEN", None)

    if token is None:
        pytest.fail("Expected environment variable DO_TOKEN")

    client = GeneratedClient(token)
    return client


@pytest.fixture(scope="session")
def public_key() -> bytes:
    """Create SSH public key material."""
    key = rsa.generate_private_key(
        backend=crypto_default_backend(), public_exponent=65537, key_size=2048
    )

    public_key_material = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH, crypto_serialization.PublicFormat.OpenSSH
    )

    return public_key_material
