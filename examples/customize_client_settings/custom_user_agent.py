from os import environ

from pydo import Client

# Define a custom value for your application's user-agent
USER_AGENT = "droplets-example"

token = environ.get("DIGITALOCEAN_TOKEN")
if token == "":
    raise Exception("No DigitalOcean API token in DIGITALOCEAN_TOKEN env var")

if environ.get("DO_OVERWRITE_AGENT"):
    # When the `user_agent_overwrite` client setting is True, the `user_agent` value
    # sent in the operation method will overwrite the full user agent.
    client = Client(token, user_agent=USER_AGENT, user_agent_overwrite=True)
    droplets_resp = client.droplets.list(f"{USER_AGENT}-overwritten")
else:
    # By default, setting the `user_agent` will prefix the full user agent (which includes
    # version details about the generated client, the sdk, and the os/platform)
    client = Client(token, user_agent=USER_AGENT)
    droplets_resp = client.droplets.list()

total = droplets_resp["meta"]["total"]

print(f"TOTAL DROPLETS ({total})\n")
print("ID\tNAME\tSTATUS")
for d in droplets_resp["droplets"]:
    print(f"{d['id']}\t{d['name']}\t{d['status']}")
