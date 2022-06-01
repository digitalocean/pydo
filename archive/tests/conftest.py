from os import environ

import pytest

from digitalocean import defaults
from digitalocean.droplets import DropletSingleCreate


@pytest.fixture(scope="module")
def token():
    token = environ.get("DO_TOKEN", None)

    if token is None:
        pytest.fail("Expected environment variable DO_TOKEN")
        return ""

    return token


@pytest.fixture
def basic_single_droplet_create():
    return DropletSingleCreate(
        name="autorest-test",
        region=defaults.REGION,
        size=defaults.SIZE,
        image=defaults.IMAGE,
        ssh_keys=["eb:d3:3e:80:76:c7:2a:79:94:2e:ca:86:d7:0d:5d:ef"],
    )
