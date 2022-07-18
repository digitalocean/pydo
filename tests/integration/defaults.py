"""Integration tests default values

Overwrite default values with environment variables.
"""

from os import environ

PREFIX = "cgtest"

# CUSTOMIZABLE
DROPLET_SIZE = environ.get("DO_DROPLET_SIZE") or "s-1vcpu-1gb"
DROPLET_IMAGE = environ.get("DO_DROPLET_IMAGE") or "ubuntu-22-04-x64"

K8S_VERSION = environ.get("DO_K8S_VERSION") or "latest"
K8S_NODE_SIZE = environ.get("DO_K8S_NODE_SIZE") or "s-1vcpu-2gb"

REGION = environ.get("DO_REGION") or "nyc3"
