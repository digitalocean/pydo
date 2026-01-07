"""Integration tests default values

Overwrite default values with environment variables.
"""

from os import environ

# Prefix used for naming test resources
PREFIX = "cgtest"

# Default droplet size slug. Override with DO_DROPLET_SIZE.
DROPLET_SIZE = environ.get("DO_DROPLET_SIZE") or "s-1vcpu-1gb"

# Default droplet image slug. Override with DO_DROPLET_IMAGE.
DROPLET_IMAGE = environ.get("DO_DROPLET_IMAGE") or "ubuntu-22-04-x64"

# Default Kubernetes version. Override with DO_K8S_VERSION.
K8S_VERSION = environ.get("DO_K8S_VERSION") or "latest"

# Default size slug for Kubernetes nodes. Override with DO_K8S_NODE_SIZE.
K8S_NODE_SIZE = environ.get("DO_K8S_NODE_SIZE") or "s-1vcpu-2gb"

# Default region for resource creation. Override with DO_REGION.
REGION = environ.get("DO_REGION") or "nyc3"

# UUID used for invoice PDF tests. Override with DO_INVOICE_UUID.
INVOICE_UUID_PARM = environ.get("DO_INVOICE_UUID") or "something"
