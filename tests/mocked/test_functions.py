"""Mock tests for the functions API resource"""

import responses

from pydo import Client


@responses.activate
def test_create_namespace(mock_client: Client, mock_client_url):
    """Mocks the functions create namespace operation"""

    expected = {
        "namespace": {
            "api_host": "https://api_host.io",
            "namespace": "fn-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "created_at": "2022-09-14T04:16:45Z",
            "updated_at": "2022-09-14T04:16:45Z",
            "label": "my namespace",
            "region": "nyc1",
            "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "key": "d1zcd455h01mqjfs4s2eaewyejehi5f2uj4etqq3h7cera8iwkub6xg5of1wdde2",
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/functions/namespaces",
        json=expected,
        status=200,
    )

    req = {"region": "nyc1", "label": "my namespace"}

    resp = mock_client.functions.create_namespace(body=req)

    assert expected == resp


@responses.activate
def test_create_trigger(mock_client: Client, mock_client_url):
    """Mocks the functions create trigger operation"""

    namespace_id = "fn-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    expected = {
        "trigger": {
            "namespace": namespace_id,
            "name": "my trigger",
            "function": "hello",
            "type": "SCHEDULED",
            "is_enabled": True,
            "created_at": "2022-11-11T04:16:45Z",
            "updated_at": "2022-11-11T04:16:45Z",
            "scheduled_details": {
                "cron": "* * * * *",
                "body": {"name": "Welcome to DO!"},
            },
            "scheduled_runs": {
                "last_run_at": "2022-11-11T04:16:45Z",
                "next_run_at": "2022-11-11T04:16:45Z",
            },
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/functions/namespaces/{namespace_id}/triggers",
        json=expected,
        status=200,
    )

    req = {
        "name": "my trigger",
        "function": "hello",
        "type": "SCHEDULED",
        "is_enabled": True,
        "scheduled_details": {"cron": "* * * * *", "body": {"name": "Welcome to DO!"}},
    }

    resp = mock_client.functions.create_trigger(namespace_id, body=req)

    assert expected == resp


@responses.activate
def test_delete_namespace(mock_client: Client, mock_client_url):
    """Mocks the functions delete namespace operation"""

    namespace_id = "fn-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/functions/namespaces/{namespace_id}",
        status=204,
    )

    del_resp = mock_client.functions.delete_namespace(namespace_id)

    assert del_resp is None


@responses.activate
def test_delete_trigger(mock_client: Client, mock_client_url):
    """Mocks the functions delete trigger operation"""

    namespace_id = "fn-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    trigger_name = "my trigger"

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/functions/namespaces/"
        f"{namespace_id}/triggers/{trigger_name}",
        status=204,
    )

    del_resp = mock_client.functions.delete_trigger(namespace_id, trigger_name)

    assert del_resp is None


@responses.activate
def test_get_namespace(mock_client: Client, mock_client_url):
    """Mocks the functions get namespace operation"""

    namespace_id = "fn-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    expected = {
        "namespace": {
            "api_host": "https://api_host.io",
            "namespace": namespace_id,
            "created_at": "2022-09-14T04:16:45Z",
            "updated_at": "2022-09-14T04:16:45Z",
            "label": "my namespace",
            "region": "nyc1",
            "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "key": "d1zcd455h01mqjfs4s2eaewyejehi5f2uj4etqq3h7cera8iwkub6xg5of1wdde2",
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/functions/namespaces/{namespace_id}",
        json=expected,
        status=200,
    )

    resp = mock_client.functions.get_namespace(namespace_id)

    assert expected == resp


@responses.activate
def test_get_trigger(mock_client: Client, mock_client_url):
    """Mocks the functions get trigger operation"""

    namespace_id = "fn-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    trigger_name = "my trigger"

    expected = {
        "trigger": {
            "namespace": namespace_id,
            "name": trigger_name,
            "function": "hello",
            "type": "SCHEDULED",
            "is_enabled": True,
            "created_at": "2022-11-11T04:16:45Z",
            "updated_at": "2022-11-11T04:16:45Z",
            "scheduled_details": {
                "cron": "* * * * *",
                "body": {"name": "Welcome to DO!"},
            },
            "scheduled_runs": {
                "last_run_at": "2022-11-11T04:16:45Z",
                "next_run_at": "2022-11-11T04:16:45Z",
            },
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/functions/namespaces/"
        f"{namespace_id}/triggers/{trigger_name}",
        json=expected,
        status=200,
    )

    resp = mock_client.functions.get_trigger(namespace_id, trigger_name)

    assert expected == resp


@responses.activate
def test_list_namespaces(mock_client: Client, mock_client_url):
    """Mocks the functions list namespaces operation"""

    expected = {
        "namespaces": [
            {
                "api_host": "https://api_host.io",
                "namespace": "fn-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "created_at": "2022-09-14T04:16:45Z",
                "updated_at": "2022-09-14T04:16:45Z",
                "label": "my namespace",
                "region": "nyc1",
                "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "key": "d1zcd455h01mqjfs4s2eaewyejehi5f"
                "2uj4etqq3h7cera8iwkub6xg5of1wdde2",
            }
        ]
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/functions/namespaces",
        json=expected,
        status=200,
    )

    resp = mock_client.functions.list_namespaces()

    assert expected == resp


@responses.activate
def test_list_triggers(mock_client: Client, mock_client_url):
    """Mocks the functions list triggers operation"""

    namespace_id = "fn-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    expected = {
        "triggers": [
            {
                "namespace": namespace_id,
                "name": "my trigger",
                "function": "hello",
                "type": "SCHEDULED",
                "is_enabled": True,
                "created_at": "2022-11-11T04:16:45Z",
                "updated_at": "2022-11-11T04:16:45Z",
                "scheduled_details": {
                    "cron": "* * * * *",
                    "body": {"name": "Welcome to DO!"},
                },
                "scheduled_runs": {
                    "last_run_at": "2022-11-11T04:16:45Z",
                    "next_run_at": "2022-11-11T04:16:45Z",
                },
            }
        ]
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/functions/namespaces/{namespace_id}/triggers",
        json=expected,
        status=200,
    )

    resp = mock_client.functions.list_triggers(namespace_id)

    assert expected == resp


@responses.activate
def test_update_trigger(mock_client: Client, mock_client_url):
    """Mocks the functions update trigger operation"""

    namespace_id = "fn-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    trigger_name = "my trigger"

    expected = {
        "trigger": {
            "namespace": namespace_id,
            "name": trigger_name,
            "function": "hello",
            "type": "SCHEDULED",
            "is_enabled": True,
            "created_at": "2022-11-11T04:16:45Z",
            "updated_at": "2022-11-11T04:16:45Z",
            "scheduled_details": {
                "cron": "* * * * *",
                "body": {"name": "Welcome to DO!"},
            },
            "scheduled_runs": {
                "last_run_at": "2022-11-11T04:16:45Z",
                "next_run_at": "2022-11-11T04:16:45Z",
            },
        }
    }

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/functions/namespaces/"
        f"{namespace_id}/triggers/{trigger_name}",
        json=expected,
        status=200,
    )

    req = {
        "is_enabled": True,
        "scheduled_details": {"cron": "* * * * *", "body": {"name": "Welcome to DO!"}},
    }

    resp = mock_client.functions.update_trigger(namespace_id, trigger_name, body=req)

    assert expected == resp
