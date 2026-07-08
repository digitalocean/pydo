"""Async chat completion via ``pydo.inference.aio.Client``.

Mirrors ``chat_completion_stream.py`` but uses the async client so it can
be embedded in an ``asyncio`` event loop alongside other concurrent work.
The surface is identical to the sync namespace — same constructor, same
operation groups, just ``await`` the calls and use ``async with`` so the
underlying aiohttp session closes cleanly.

Usage:
    # The PAT must be created with FULL ACCESS scope to call inference APIs.
    export DIGITALOCEAN_TOKEN="your-full-access-pat"
    python examples/inference/async_chat_completion.py
"""

import asyncio
import os

from pydo.inference.aio import Client


async def main() -> None:
    async with Client(token=os.environ["DIGITALOCEAN_TOKEN"]) as client:
        resp = await client.chat.completions.create(
            model="llama3.3-70b-instruct",
            messages=[
                {
                    "role": "user",
                    "content": "Give me a one-sentence fun fact about octopuses.",
                }
            ],
            max_tokens=128,
        )

        print(resp.choices[0].message.content)


if __name__ == "__main__":
    asyncio.run(main())
