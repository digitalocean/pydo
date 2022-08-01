""" test_projects.py
    Integration Tests for Projects
"""

import uuid

from digitalocean import Client
from tests.integration import defaults


def test_projects(integration_client: Client):
    """Tests creating, updating, and deleting a project"""

    # test creating the project
    expected_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    create_req = {
        "name": expected_name,
        "description": "Test project for python client",
        "purpose": "testing",
        "environment": "Development",
    }
    create_resp = integration_client.projects.create(body=create_req)
    assert create_resp["project"]["name"] == expected_name

    project_id = create_resp["project"]["id"]

    # test getting a project
    get_resp = integration_client.projects.get(project_id=project_id)
    assert get_resp["project"]["name"] == expected_name

    # test updating a project
    updated_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    update_req = {
        "name": updated_name,
        "description": "Test project for python client",
        "purpose": "testing",
        "environment": "Development",
        "is_default": False,
    }
    update_resp = integration_client.projects.update(
        project_id=project_id, body=update_req
    )
    assert update_resp["project"]["name"] == updated_name

    # test patching a project
    patch_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    patch_req = {
        "name": patch_name,
    }
    patch_resp = integration_client.projects.patch(
        project_id=project_id, body=patch_req
    )
    assert patch_resp["project"]["name"] == patch_name

    # test listing a project
    list_resp = integration_client.projects.list()
    # there should always be atleast a default project
    assert len(list_resp["projects"]) > 0

    # test deleting a project
    # Work around endpoint requiring "application/json" for DELETES even though
    # there is no request or response body.
    custom_headers = {"Content-Type": "application/json"}
    delete_resp = integration_client.projects.delete(
        headers=custom_headers, project_id=project_id
    )
    assert delete_resp is None


def test_projects_default(integration_client: Client):
    """Testing GETting, updating, patching, getting the default Project operation"""

    # test getting the default project
    get_resp = integration_client.projects.get_default()
    assert get_resp["project"]["is_default"]

    # test updating the default project
    expected_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    update_req = {
        "name": expected_name,
        "description": "Test project for python client",
        "purpose": "testing",
        "environment": "Development",
        "is_default": True,
    }
    update_resp = integration_client.projects.update_default(body=update_req)
    assert update_resp["project"]["name"] == expected_name
    assert update_resp["project"]["is_default"]


    # test patching the default project
    expected_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    patch_req = {
        "name": expected_name,
    }
    patch_resp = integration_client.projects.patch_default(body=patch_req)
    assert patch_resp["project"]["name"] == expected_name
    assert patch_resp["project"]["is_default"]
