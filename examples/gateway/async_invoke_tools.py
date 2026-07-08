"""Async Action Gateway usage: list, invoke, and execute code.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
"""

import asyncio
import os

from pydo.aio import Client


async def main() -> None:
    client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])

    tools = await client.gateway.tools.list(include_all=True)
    print("catalog:", [tool.name for tool in tools])

    output = await client.gateway.tools.invoke_one(
        "web_search", {"query": "DigitalOcean Gradient", "max_results": 2}
    )
    print("web_search output:", str(output)[:200])

    result = await client.gateway.code.execute("print('hello from async')")
    print("code stdout:", result.get("stdout"))

    await client.close()


asyncio.run(main())
