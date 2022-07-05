from os import environ

PREFIX = "cgtest"

DROPLET_SIZE = environ.get('DO_DROPLET_SIZE') or "s-1vcpu-1gb"
DROPLET_IMAGE = environ.get('DO_DROPLET_IMAGE') or "ubuntu-22-04-x64"
DATABASE_SIZE = environ.get('DO_DATABASE_SIZE') or "db-s-1vcpu-1gb"

REGION = environ.get('DO_REGION') or "nyc3"
