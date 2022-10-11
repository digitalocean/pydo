import random
import string
from os import environ

from pydo import Client

KUBERNETES_VERSION = "latest"
REGION = "nyc3"
TIMEOUT_APP = 120
TIMEOUT_KUBERNETES_CREATE = 1200

token = environ.get("DO_TOKEN")
if token == "":
    raise Exception("No DigitalOcean API token in DO_TOKEN env var")

# Overwrite the default timeout set by the client with your own
client = Client(token, timeout=TIMEOUT_APP)

# Normal operation calls will use the app's timeout
clusters_resp = client.kubernetes.list_clusters()
total = clusters_resp["meta"]["total"]

print(f"TOTAL CLUSTERS ({total})\n")
print("ID\tNAME\tSTATE")
for d in clusters_resp["kubernetes_clusters"]:
    print(f"{d['id']}\t{d['name']}\t{d['status']['state']}")

rnd_suffix = s = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
new_cluster_req = {
    "name": f"example-cluster-{rnd_suffix}",
    "region": REGION,
    "version": KUBERNETES_VERSION,
    "node_pools": [{"size": "s-1vcpu-2gb", "count": 3, "name": "worker-pool"}],
}

# Setting the `timeout` kwarg value for a specific operation method call will overwrite
# the timeout for that request.
cluster_create_resp = client.kubernetes.create_cluster(new_cluster_req, timeout=1200)
# Note: This method was chosen for the sake of the example. The `cteate_cluster`
# kubernetes operation isn't a log running process (unlike the background action that
# tracks the clusters provisioning state).

new_cluster_id = cluster_create_resp["kubernetes_cluster"]["id"]
new_cluster_name = cluster_create_resp["kubernetes_cluster"]["name"]
new_cluster_created_at = cluster_create_resp["kubernetes_cluster"]["created_at"]
new_cluster_status = cluster_create_resp["kubernetes_cluster"]["status"]["message"]
print(f"New cluster: Name {new_cluster_name} (ID: {new_cluster_id})")
print(f"New cluster: created at {new_cluster_created_at}")
print(f"New cluster: Status: {new_cluster_status}")
