"""Async Action Gateway session: list, invoke, and execute code.

Required env:
  DIGITALOCEAN_TOKEN

Optional env:
  PYDO_GATEWAY_ENDPOINT   preview: https://actions.do-ai-test.run
  ACTOR_ID
"""

import asyncio
import os

from pydo.action_gateway.aio import ActionGatewayClient


async def main() -> None:
    client = ActionGatewayClient(token=os.environ["DIGITALOCEAN_TOKEN"])
    session = await client.session.create(
        actor_id=os.environ.get("ACTOR_ID", "example-user"),
        permissions={
            "default_action": "ask",
            "rules": [
                {"tool": "exa_web_search", "action": "allow"},
                {"tool": "execute_code", "action": "allow"},
            ],
        },
    )

    tools = await session.tools.list(include_all=True)
    print("session tools:", [tool.name for tool in tools])
    print("MCP URL:", session.url)

    output = await session.tools.invoke_one(
        "exa_web_search", {"query": "DigitalOcean Gradient", "max_results": 2}
    )
    print("web_search output:", str(output)[:200])

    result = await session.code.execute("print('hello from async')")
    print("code stdout:", result.get("stdout"))

    await client.close()


asyncio.run(main())
