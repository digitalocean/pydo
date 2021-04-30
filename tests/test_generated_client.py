import time

import pytest

from digitalocean.droplets import Droplet, DropletsAPI, exceptions


def test_droplet_create(token, basic_single_droplet_create):
    droplet_api = DropletsAPI(token)
    req = basic_single_droplet_create

    droplet, action_id = droplet_api.create_single(req)
    assert type(droplet) is Droplet
    assert droplet.id > 0
    assert droplet.name == req.name
    assert type(action_id) is int
    assert action_id > 0

    time.sleep(30)
    droplet = droplet_api.get(droplet.id)
    assert droplet.status == "active"

    new_name = f"{droplet.name}-renamed"
    droplet_api.rename(droplet_id=droplet.id, new_name=new_name)

    time.sleep(15)
    droplet = droplet_api.get(droplet.id)
    assert droplet.name == new_name

    deleted = droplet_api.delete(droplet.id)
    assert deleted

    time.sleep(10)
    with pytest.raises(exceptions.Unprocessable):
        droplet_api.get(droplet.id)
