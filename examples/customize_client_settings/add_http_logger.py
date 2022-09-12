import logging
import os

from digitalocean import Client

LOG_FILE = "simple_ssh_keys.log"

# Initialize the application logger
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

token = os.environ.get("DO_TOKEN")
if token == "":
    raise Exception("No DigitalOcean API token in DO_TOKEN env var")
# Initialize the client with the `logger` kwarg set to the application's logger.
client = Client(
    token,
    logger=LOGGER,
)

keys_resp = client.ssh_keys.list()
total = keys_resp["meta"]["total"]

print(f"TOTAL SSH KEYS ({total})\n")
print("ID\tNAME\tFINGERPRINT")
for d in keys_resp["ssh_keys"]:
    print(f"{d['id']}\t{d['name']}\t{d['fingerprint']}")

print(f"\nView the HTTP log: {LOG_FILE}")
