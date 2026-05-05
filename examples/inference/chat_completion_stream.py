"""Stream a chat completion from the Gradient AI Platform token-by-token.

Usage:
    # The PAT must be created with FULL ACCESS scope to call inference APIs.
    export DIGITALOCEAN_TOKEN="your-full-access-pat"
    python examples/inference/chat_completion_stream.py
"""

import os

from pydo import Client


def main() -> None:
    client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])

    stream = client.chat.completions.create(
        model="llama3.3-70b-instruct",
        messages=[
            {
                "role": "user",
                "content": "Tell me some fun facts about sharks.",
            }
        ],
        max_tokens=512,
        stream=True,
    )

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        piece = delta.get("reasoning_content") or delta.get("content")
        if piece:
            print(piece, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
