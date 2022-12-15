"""Mock tests for the Projects API resource"""

import responses
from responses import matchers

from pydo import Client



@responses.activate
def test_projects_list(mock_client: Client, mock_client_url):
    """Mocks the projects list operation"""
    expected = {
        "projects": [
            {
                "id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
                "owner_uuid": "99525febec065ca37b2ffe4f852fd2b2581895e7",
                "owner_id": 258992,
                "name": "my-web-api",
                "description": "My website API",
                "purpose": "Service or API",
                "environment": "Production",
                "is_default": "false",
                "created_at": "2018-09-27T20:10:35Z",
                "updated_at": "2018-09-27T20:10:35Z",
            },
            {
                "id": "addb4547-6bab-419a-8542-76263a033cf6",
                "owner_uuid": "99525febec065ca37b2ffe4f852fd2b2581895e7",
                "owner_id": 258992,
                "name": "Default",
                "description": "Default project",
                "purpose": "Just trying out DigitalOcean",
                "environment": "Development",
                "is_default": "true",
                "created_at": "2017-10-19T21:44:20Z",
                "updated_at": "2019-11-05T18:50:03Z",
            },
        ],
        "links": {
            "pages": {
                "first": "https://api.digitalocean.com/v2/projects?page=1",
                "last": "https://api.digitalocean.com/v2/projects?page=1",
            }
        },
        "meta": {"total": 2},
    }

    responses.add(responses.GET, f"{mock_client_url}/v2/projects", json=expected)
    list_resp = mock_client.projects.list()

    assert list_resp == expected


@responses.activate
def test_projects_list_with_pagination(mock_client: Client, mock_client_url):
    """Mocks the projects list operation"""
    expected = {
        "projects": [
            {
                "id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
                "owner_uuid": "99525febec065ca37b2ffe4f852fd2b2581895e7",
                "owner_id": 258992,
                "name": "my-web-api",
                "description": "My website API",
                "purpose": "Service or API",
                "environment": "Production",
                "is_default": "false",
                "created_at": "2018-09-27T20:10:35Z",
                "updated_at": "2018-09-27T20:10:35Z",
            },
            {
                "id": "addb4547-6bab-419a-8542-76263a033cf6",
                "owner_uuid": "99525febec065ca37b2ffe4f852fd2b2581895e7",
                "owner_id": 258992,
                "name": "Default",
                "description": "Default project",
                "purpose": "Just trying out DigitalOcean",
                "environment": "Development",
                "is_default": "true",
                "created_at": "2017-10-19T21:44:20Z",
                "updated_at": "2019-11-05T18:50:03Z",
            },
        ],
        "links": {
            "pages": {
                "first": "https://api.digitalocean.com/v2/projects?page=2&per_page=20",
                "last": "https://api.digitalocean.com/v2/projects?page=6&per_page=20",
            }
        },
        "meta": {"total": 6},
    }

    params = {"per_page": 20, "page": 1}
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/projects",
        json=expected,
        match=[matchers.query_param_matcher(params)],
    )
    list_resp = mock_client.projects.list()

    assert list_resp == expected


@responses.activate
def test_projects_create(mock_client: Client, mock_client_url):
    """Tests Projects Creation"""
    expected = {
        "project": {
            "id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
            "owner_uuid": "99525febec065ca37b2ffe4f852fd2b2581895e7",
            "owner_id": 258992,
            "name": "my-web-api",
            "description": "My website API",
            "purpose": "Service or API",
            "environment": "Production",
            "created_at": "2018-09-27T20:10:35Z",
            "updated_at": "2018-09-27T20:10:35Z",
            "is_default": "false",
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/projects",
        json=expected,
        status=201,
    )

    create_resp = mock_client.projects.create(
        {
            "name": "my-web-api",
            "description": "My website API",
            "purpose": "Service or API",
            "environment": "Production",
        }
    )

    assert create_resp == expected


@responses.activate
def test_projects_get(mock_client: Client, mock_client_url):
    """Test Projects Get by Name"""
    expected = {
        "project": {
            "id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
            "owner_uuid": "99525febec065ca37b2ffe4f852fd2b2581895e7",
            "owner_id": 258992,
            "name": "my-web-api",
            "description": "My website API",
            "purpose": "Service or API",
            "environment": "Production",
            "created_at": "2018-09-27T20:10:35Z",
            "updated_at": "2018-09-27T20:10:35Z",
            "is_default": "false",
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/projects/4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
        json=expected,
        status=200,
    )

    get_resp = mock_client.projects.get(
        project_id="4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679"
    )

    assert get_resp == expected


@responses.activate
def test_projects_delete(mock_client: Client, mock_client_url):
    """Test Projects Delete"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/projects/4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
        status=204,
    )
    del_resp = mock_client.projects.delete(
        project_id="4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679"
    )

    assert del_resp is None


@responses.activate
def test_projects_update(mock_client: Client, mock_client_url):
    """Test Project Update"""
    expected = {
        "project": {
            "id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
            "owner_uuid": "99525febec065ca37b2ffe4f852fd2b2581895e7",
            "owner_id": 258992,
            "name": "my-web-api",
            "description": "My website API",
            "purpose": "Service or API",
            "environment": "Production",
            "created_at": "2018-09-27T20:10:35Z",
            "updated_at": "2018-09-27T20:10:35Z",
            "is_default": "false",
        }
    }

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/projects/4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
        json=expected,
        status=200,
    )

    update_resp = mock_client.projects.update(
        project_id="4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
        body={
            "project": {
                "id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
                "owner_uuid": "99525febec065ca37b2ffe4f852fd2b2581895e7",
                "owner_id": 258992,
                "name": "my-web-api",
                "description": "My website API",
                "purpose": "Service or API",
                "environment": "Production",
                "created_at": "2018-09-27T20:10:35Z",
                "updated_at": "2018-09-27T20:10:35Z",
                "is_default": "false",
            }
        },
    )

    assert update_resp == expected


@responses.activate
def test_projects_patch(mock_client: Client, mock_client_url):
    """Test Projects Patch"""
    expected = {"name": "my-web-api"}

    responses.add(
        responses.PATCH,
        f"{mock_client_url}/v2/projects/4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
        json=expected,
        status=200,
    )

    patch_resp = mock_client.projects.patch(
        project_id="4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
        body={
            "project": {
                "id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
                "owner_uuid": "99525febec065ca37b2ffe4f852fd2b2581895e7",
                "owner_id": 258992,
                "name": "my-web-api",
                "description": "My website API",
                "purpose": "Service or API",
                "environment": "Production",
                "created_at": "2018-09-27T20:10:35Z",
                "updated_at": "2018-09-27T20:10:35Z",
                "is_default": "false",
            }
        },
    )

    assert patch_resp == expected


@responses.activate
def test_projects_get_default(mock_client: Client, mock_client_url):
    """Test Projects Get Default"""
    expected = {
        "project": {
            "id": "addb4547-6bab-419a-8542-76263a033cf6",
            "owner_uuid": "99525febec065ca37b2ffe4f852fd2b2581895e7",
            "owner_id": 258992,
            "name": "Default",
            "description": "Default project",
            "purpose": "Just trying out DigitalOcean",
            "environment": "Development",
            "is_default": "true",
            "created_at": "2017-10-19T21:44:20Z",
            "updated_at": "2019-11-05T18:50:03Z",
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/projects/default",
        json=expected,
        status=200,
    )

    get_resp = mock_client.projects.get_default()
    assert get_resp == expected


@responses.activate
def test_projects_update_default(mock_client: Client, mock_client_url):
    """Test Project Update Default"""
    expected = {
        "project": {
            "id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
            "owner_uuid": "99525febec065ca37b2ffe4f852fd2b2581895e7",
            "owner_id": 258992,
            "name": "my-web-api",
            "description": "My website API",
            "purpose": "Service or API",
            "environment": "Production",
            "created_at": "2018-09-27T20:10:35Z",
            "updated_at": "2018-09-27T20:10:35Z",
            "is_default": "false",
        }
    }

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/projects/default",
        json=expected,
        status=200,
    )

    update_resp = mock_client.projects.update_default(
        body={
            "name": "my-web-api",
            "description": "My website API",
            "purpose": "Service or API",
            "environment": "Production",
            "is_default": "false",
        },
    )

    assert update_resp == expected


@responses.activate
def test_projects_patch_default(mock_client: Client, mock_client_url):
    """Test Project Patch Default"""
    expected = {
        "project": {
            "id": "4e1bfbc3-dc3e-41f2-a18f-1b4d7ba71679",
            "owner_uuid": "99525febec065ca37b2ffe4f852fd2b2581895e7",
            "owner_id": 258992,
            "name": "my-web-api",
            "description": "My website API",
            "purpose": "Service or API",
            "environment": "Production",
            "created_at": "2018-09-27T20:10:35Z",
            "updated_at": "2018-09-27T20:10:35Z",
            "is_default": "false",
        }
    }

    responses.add(
        responses.PATCH,
        f"{mock_client_url}/v2/projects/default",
        json=expected,
        status=200,
    )

    update_resp = mock_client.projects.patch_default(
        body={
            "name": "my-web-api",
        },
    )

    assert update_resp == expected
