""" test_projects.py
    Integration Tests for Projects
"""

import uuid

from digitalocean import Client
from tests.integration import defaults


def test_projects_list(integration_client: Client):
    """Testing the list of all Projects"""

    list_resp = integration_client.projects.list()

    # only project that should exist is default
    assert list_resp["projects"][0]["is_default"]

    integration_client.projects.delete(
        project_id="f8cc2d39-5d36-4406-8a42-9d31b92ba0dd"
    )


def test_projects_create(integration_client: Client):
    """Testing the POST a new Project operation"""

    expected_name = f"{defaults.PREFIX}-{uuid.uuid4()}"

    create_req = {
        "name": expected_name,
        "description": "Test project for python client",
        "purpose": "testing",
        "environment": "Development",
    }

    create_resp = integration_client.projects.create(create_req)
    assert create_resp["project"]["name"] == expected_name
    delete_resp = integration_client.projects.delete(create_resp["project"]["id"])
    print(delete_resp)

    # client = integration_client
    # with shared.with_test_project(client, **create_req) as project:
    #     assert project["project"]["name"] == expected_name


def test_projects_get_default(integration_client: Client):
    """Testing GETting the default Project operation"""

    get_resp = integration_client.projects.get_default()

    # only project that should exist is default
    assert get_resp["project"]["is_default"]


def test_projects_update_default(integration_client: Client):
    """Testing updating the default project operation"""

    expected_name = f"{defaults.PREFIX}-{uuid.uuid4()}"

    update_req = {
        "name": expected_name,
        "description": "Test project for python client",
        "purpose": "testing",
        "environment": "Development",
    }

    create_resp = integration_client.projects.create(body=update_req)

    # only project that should exist is default
    assert create_resp["project"]["name"] == expected_name


def test_projects_delete(integration_client: Client):
    """Testing delete a project operation"""

    expected_name = f"{defaults.PREFIX}-{uuid.uuid4()}"

    create_req = {
        "name": expected_name,
        "description": "Test project for python client",
        "purpose": "testing",
        "environment": "Development",
    }

    create_resp = integration_client.projects.create(body=create_req)
    assert create_resp["project"]["name"] == expected_name
    proj_id = create_resp["project"]["id"]

    delete_resp = integration_client.projects.delete(project_id=proj_id)

    assert delete_resp is None
