"""List every inference model available to the current Gradient account.

Usage:
    # The PAT must be created with FULL ACCESS scope to call inference APIs.
    export DIGITALOCEAN_TOKEN="your-full-access-pat"
    python examples/inference/list_models.py
"""

import os

from pydo import Client


def main() -> None:
    client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])

    models = client.models.list()
    for model in models["data"]:
        print(model["id"])


if __name__ == "__main__":
    main()
