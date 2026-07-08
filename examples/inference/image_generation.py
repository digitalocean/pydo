"""Generate an image with the Gradient AI Platform and save it to disk.

Uses the inference-focused ``pydo.inference.Client`` entry point so the
top-level surface (``dir(client)``, IDE autocomplete) stays focused on
inference primitives.
Usage:
    # The PAT must be created with FULL ACCESS scope to call inference APIs.
    export DIGITALOCEAN_TOKEN="your-full-access-pat"
    python examples/inference/image_generation.py
"""

import base64
import os

from pydo.inference import Client


def main() -> None:
    client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])

    result = client.images.generate(
        model="openai-gpt-image-1",
        prompt="A friendly shark typing on a laptop at a sunny beach",
        n=1,
    )

    output_path = "output.png"
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(result.data[0].b64_json))

    print(f"Image saved as {output_path}")


if __name__ == "__main__":
    main()
