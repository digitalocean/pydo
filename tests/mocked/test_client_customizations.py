"""Client customization tests

These tests aren't essential but serve as good examples for using the client with
custom configuration.
"""
import logging
import re

import responses
from digitalocean import Client

# pylint: disable=missing-function-docstring


def test_custom_headers():
    custom_headers = {"x-request-id": "fakeid"}
    client = Client("", headers=custom_headers)

    # pylint: disable=protected-access
    assert client._client._config.headers_policy.headers == custom_headers


def test_custom_timeout():
    timeout = 300
    client = Client("", timeout=timeout)

    # pylint: disable=protected-access
    assert client._client._config.retry_policy.timeout == timeout


def test_custom_endpoint():
    endpoint = "https://fake.local"
    client = Client("", endpoint=endpoint)

    # pylint: disable=protected-access
    assert client._client._base_url == endpoint


def test_custom_logger():
    name = "mockedtests"
    logger = logging.getLogger(name)
    client = Client("", logger=logger)

    # pylint: disable=protected-access
    assert client._client._config.http_logging_policy.logger.name == name


@responses.activate
def test_custom_user_agent():
    user_agent = "test"
    fake_endpoint = "https://fake.local"
    client = Client(
        "",
        endpoint=fake_endpoint,
        user_agent=user_agent,
        user_agent_overwrite=True,
    )

    full_user_agent_pattern = (
        r"^test azsdk-python-digitaloceanclient\/.+Python\/.+\(.+\)$"
    )
    # pylint: disable=protected-access
    got_user_agent = client._client._config.user_agent_policy.user_agent
    match = re.match(full_user_agent_pattern, got_user_agent)
    assert match is not None

    fake_url = f"{fake_endpoint}/v2/account"
    responses.add(
        responses.GET,
        fake_url,
        match=[responses.matchers.header_matcher({"User-Agent": user_agent})],
    )

    client.account.get(user_agent=user_agent)
    assert responses.assert_call_count(fake_url, count=1)
