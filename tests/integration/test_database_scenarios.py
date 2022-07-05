import defaults
import random
import string

from digitalocean import DigitalOceanClient


def test_database_create_mongodb(integration_client: DigitalOceanClient):
    name = f"mdb-{''.join(random.choices(string.ascii_lowercase, k=8))}"

    database_req = {
        "name": name,
        "engine": "mongodb",
        "version": "4",
        "region": defaults.REGION,
        "size": defaults.DATABASE_SIZE,
        "num_nodes": 1,
    }

    database_create_resp = integration_client.databases.create_cluster(database_req)

    assert database_create_resp['database']['name'] == name
    assert database_create_resp['database']['status'] == "creating"
