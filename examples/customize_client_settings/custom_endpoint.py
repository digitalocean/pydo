from os import environ

from pydo import Client

# Set the DO_ENDPOINT environment variable to a valid endpoint
ENDPOINT = environ.get("DO_ENDPOINT") or "https://my.proxy"

token = environ.get("DO_TOKEN")
if token == "":
    raise Exception("No DigitalOcean API token in DO_TOKEN env var")

# Initialize the client with the `endpoint` kwarg set to the custom endpoint.
client = Client(token, endpoint=ENDPOINT)
droplets_resp = client.droplets.list()

total = droplets_resp["meta"]["total"]

print(f"TOTAL DROPLETS ({total})\n")
print("ID\tNAME\tSTATUS")
for d in droplets_resp["droplets"]:
    print(f"{d['id']}\t{d['name']}\t{d['status']}")
