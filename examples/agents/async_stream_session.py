"""Async stream session events. Set DIGITALOCEAN_TOKEN and SESSION_ID."""

import asyncio
import os

from pydo.aio import Client

SESSION_ID = os.environ["SESSION_ID"]


async def main() -> None:
    async with Client(token=os.environ["DIGITALOCEAN_TOKEN"]) as client:
        stream = await client.agents.sessions.stream(SESSION_ID)
        async with stream as events:
            async for event in events:
                if getattr(event, "type", None) == "run.token_delta" and event.get("data"):
                    print(event.data.text, end="", flush=True)
                elif "token_chunk" in event:
                    print(event.token_chunk.text, end="", flush=True)
                else:
                    print(event)


asyncio.run(main())
