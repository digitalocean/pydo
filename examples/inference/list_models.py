"""List every inference model available to the current Gradient account.

Uses the inference-focused ``pydo.inference.Client`` entry point so the
top-level surface (``dir(client)``, IDE autocomplete) stays focused on
inference primitives.

Usage:
    # The PAT must be created with FULL ACCESS scope to call inference APIs.
    export DIGITALOCEAN_TOKEN="your-full-access-pat"
    python examples/inference/list_models.py
"""

import os

from pydo.inference import Client


def main() -> None:
    client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])

    models = client.models.list()
    for model in models["data"]:
        print(model["id"])


if __name__ == "__main__":
    main()
