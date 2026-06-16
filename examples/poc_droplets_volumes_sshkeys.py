import os, uuid
from time import sleep
from urllib.parse import urlparse
from urllib.parse import parse_qs

# Would be nice to not need azure branded imports.
from azure.core.exceptions import HttpResponseError

from pydo import Client

REGION = "nyc3"


class DigitalOceanError(Exception):
    pass


class DropletCreator:
    def __init__(self, *args, **kwargs):
        token = os.environ.get("DIGITALOCEAN_TOKEN")
        if not token:
            raise DigitalOceanError("No DigitalOcean API token in DIGITALOCEAN_TOKEN env var")
        self.client = Client(token=token)

    def throw(self, message):
        raise DigitalOceanError(message) from None

    def main(self):
        key_name = os.environ.get("SSH_KEY_NAME")
        if not key_name:
            raise DigitalOceanError("SSH_KEY_NAME not set")
        ssh_key = self.find_ssh_key(key_name)

        droplet_req = {
            "name": "test-{0}".format(str(uuid.uuid4())),
            "region": REGION,
            "size": "s-1vcpu-1gb",
            "image": "ubuntu-22-04-x64",
            "ssh_keys": [ssh_key["fingerprint"]],
        }
        droplet = self.create_droplet(droplet_req)

        volume_req = {
            "size_gigabytes": 10,
            "name": "test-{0}".format(str(uuid.uuid4())),
            "description": "Block storage testing",
            "region": REGION,
            "filesystem_type": "ext4",
        }
        volume = self.create_volume(volume_req)

        print(
            "Attaching volume {0} to Droplet {1}...".format(volume["id"], droplet["id"])
        )
        attach_req = {"type": "attach", "droplet_id": droplet["id"]}
        try:
            action_resp = self.client.volume_actions.post_by_id(
                volume["id"], attach_req
            )
            self.wait_for_action(action_resp["action"]["id"])
        except HttpResponseError as err:
            self.throw(
                "Error: {0} {1}: {2}".format(
                    err.status_code, err.reason, err.error.message
                )
            )

        print("Done!")

    def create_droplet(self, req=None):
        if req is None:
            req = {}
        print("Creating Droplet using: {0}".format(req))
        try:
            resp = self.client.droplets.create(body=req)
            droplet_id = resp["droplet"]["id"]
            self.wait_for_action(resp["links"]["actions"][0]["id"])

            get_resp = self.client.droplets.get(droplet_id)
            droplet = get_resp["droplet"]
            ip_address = ""
            for net in droplet["networks"]["v4"]:
                if net["type"] == "public":
                    ip_address = net["ip_address"]
        except HttpResponseError as err:
            self.throw(
                "Error: {0} {1}: {2}".format(
                    err.status_code, err.reason, err.error.message
                )
            )
        else:
            print(
                "Droplet ID: {0} Name: {1} IP: {2}".format(
                    droplet_id, droplet["name"], ip_address
                )
            )
            return droplet

    def wait_for_action(self, id, wait=5):
        print("Waiting for action {0} to complete...".format(id), end="", flush=True)
        status = "in-progress"
        while status == "in-progress":
            try:
                resp = self.client.actions.get(id)
            except HttpResponseError as err:
                self.throw(
                    "Error: {0} {1}: {2}".format(
                        err.status_code, err.reason, err.error.message
                    )
                )
            else:
                status = resp["action"]["status"]
                if status == "in-progress":
                    print(".", end="", flush=True)
                    sleep(wait)
                elif status == "errored":
                    raise DigitalOceanError(
                        "{0} action {1} {2}".format(
                            resp["action"]["type"], resp["action"]["id"], status
                        )
                    )
                else:
                    print(".")

    def find_ssh_key(self, name):
        print("Looking for ssh key named {0}...".format(name))
        page = 1
        paginated = True
        while paginated:
            try:
                resp = self.client.ssh_keys.list(per_page=50, page=page)
                for k in resp["ssh_keys"]:
                    if k["name"] == name:
                        print("Found ssh key: {0}".format(k["fingerprint"]))
                        return k
            except HttpResponseError as err:
                self.throw(
                    "Error: {0} {1}: {2}".format(
                        err.status_code, err.reason, err.error.message
                    )
                )

            # Fix: Use dict access for links/pages and int for page
            pages = resp.get("links", {}).get("pages", {})
            if "next" in pages:
                parsed_url = urlparse(pages["next"])
                page = int(parse_qs(parsed_url.query)["page"][0])
            else:
                paginated = False

        raise DigitalOceanError("no ssh key found")

    def create_volume(self, req=None):
        if req is None:
            req = {}
        print("Creating volume using: {0}".format(req))
        try:
            resp = self.client.volumes.create(body=req)
            volume = resp["volume"]
        except HttpResponseError as err:
            self.throw(
                "Error: {0} {1}: {2}".format(
                    err.status_code, err.reason, err.error.message
                )
            )
        else:
            print("Created volume {0} <ID: {1}>".format(volume["name"], volume["id"]))
            return volume


if __name__ == "__main__":
    dc = DropletCreator()
    dc.main()
