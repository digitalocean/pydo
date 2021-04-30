import time

import pytest

from digitalocean.droplets import Droplet, DropletsAPI, exceptions


def test_droplet_create(token, basic_single_droplet_create):
    api = DropletsAPI(token)
    req = basic_single_droplet_create

    droplet, action_id = api.create_single(req)
    assert type(droplet) is Droplet
    assert droplet.id > 0
    assert droplet.name == req.name
    assert type(action_id) is int
    assert action_id > 0

    time.sleep(30)
    droplet = api.get(droplet.id)
    assert droplet.status == "active"

    new_name = f"{droplet.name}-renamed"
    api.rename(droplet_id=droplet.id, new_name=new_name)

    time.sleep(15)
    droplet = api.get(droplet.id)
    assert droplet.name == new_name

    deleted = api.delete(droplet.id)
    assert deleted

    time.sleep(10)
    with pytest.raises(exceptions.Unprocessable):
        api.get(droplet.id)
