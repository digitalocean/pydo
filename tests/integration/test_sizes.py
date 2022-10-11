""" test_sizes.py
    Integration Test for Sizes
"""
import pytest

from pydo import Client
from pydo.aio import Client as aioClient


def test_sizes_list(integration_client: Client):
    """Testing the List of the Sizes endpoint"""
    list_resp = integration_client.sizes.list()

    assert len(list_resp["sizes"]) >= 20


@pytest.mark.asyncio
async def test_sizes_list_async(async_integration_client: aioClient):
    """Testing the List of the Sizes endpoint"""
    list_resp = await async_integration_client.sizes.list()

    assert len(list_resp["sizes"]) >= 20
