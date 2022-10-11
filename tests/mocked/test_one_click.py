"""Mock tests for the 1-click API resource."""
import responses
from responses import matchers

from pydo import Client


@responses.activate
def test_one_click_list_applications(mock_client: Client, mock_client_url):
    """Mocks the 1-clicks list applications operation."""
    expected = {
        "1_clicks": [
            {"slug": "monitoring", "type": "kubernetes"},
            {"slug": "wordpress-18-04", "type": "droplet"},
        ]
    }
    responses.add(responses.GET, f"{mock_client_url}/v2/1-clicks", json=expected)

    one_click_apps = mock_client.one_clicks.list()
    assert one_click_apps == expected


@responses.activate
def test_one_click_list_applications_with_query(mock_client: Client, mock_client_url):
    """Mocks list 1-click applications with query"""

    expected = {
        "1_clicks": [
            {"slug": "wordpress-18-04", "type": "droplet"},
        ]
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/1-clicks",
        json=expected,
        match=[matchers.query_param_matcher({"type": "droplet"})],
    )

    one_click_apps = mock_client.one_clicks.list(type="droplet")
    assert one_click_apps == expected


@responses.activate
def test_one_click_install_kubernetes(mock_client: Client, mock_client_url):
    """Mocks install kubernetes 1-click applciation"""

    expected = {"message": "Successfully kicked off addon job."}

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/1-clicks/kubernetes",
        json=expected,
    )

    install_resp = mock_client.one_clicks.install_kubernetes(expected)
    assert install_resp == expected
