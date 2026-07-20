"""Async Action Gateway session: list, invoke, and execute code.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
  END_USER_ID
"""

import asyncio
import os

from pydo.action_gateway.aio import Client


async def main() -> None:
    client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
    session = await client.sessions.create(
        end_user_id=os.environ.get("END_USER_ID", "example-user"),
    )

    tools = await session.tools.list(include_all=True)
    print("catalog:", [tool.name for tool in tools])
    print("MCP URL:", session.url)

    output = await session.tools.invoke_one(
        "web_search", {"query": "DigitalOcean Gradient", "max_results": 2}
    )
    print("web_search output:", str(output)[:200])

    result = await session.code.execute("print('hello from async')")
    print("code stdout:", result.get("stdout"))

    await client.close()


asyncio.run(main())
