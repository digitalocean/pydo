# pylint: disable=duplicate-code

""" test_load_balancers.py
    Integration tests for load balancers.
"""

import uuid

from tests.integration import defaults, shared
from digitalocean import Client


def test_load_balancers_tag(integration_client: Client, public_key: bytes):
    """
    Tests creating a load balancer with a Droplet assigned via a tag, updating
    it, and deleting it.
    """
    tag_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    droplet_req = {
        "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
        "region": defaults.REGION,
        "size": defaults.DROPLET_SIZE,
        "image": defaults.DROPLET_IMAGE,
        "tags": [tag_name],
    }

    with shared.with_test_tag(integration_client, **{"name": tag_name}):
        with shared.with_test_droplet(
            integration_client, public_key, **droplet_req
        ) as droplet:
            # Ensure Droplet create is finished before proceeding
            shared.wait_for_action(
                integration_client, droplet["links"]["actions"][0]["id"]
            )

            lb_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
            lb_create = {
                "name": lb_name,
                "region": defaults.REGION,
                "forwarding_rules": [
                    {
                        "entry_protocol": "tcp",
                        "entry_port": 80,
                        "target_protocol": "tcp",
                        "target_port": 80,
                    }
                ],
                "tag": tag_name,
            }

            with shared.with_test_load_balancer(
                integration_client, lb_create, wait=True
            ) as new_lb:
                lbid = new_lb["load_balancer"]["id"]
                assert lbid is not None
                assert new_lb["load_balancer"]["name"] == lb_name
                assert new_lb["load_balancer"]["region"]["slug"] == defaults.REGION
                assert new_lb["load_balancer"]["tag"] == tag_name
                assert new_lb["load_balancer"]["droplet_ids"] == [
                    droplet["droplet"]["id"]
                ]
                assert (
                    new_lb["load_balancer"]["forwarding_rules"][0]["entry_protocol"]
                    == "tcp"
                )
                assert (
                    new_lb["load_balancer"]["forwarding_rules"][0]["entry_port"] == 80
                )
                assert (
                    new_lb["load_balancer"]["forwarding_rules"][0]["target_protocol"]
                    == "tcp"
                )
                assert (
                    new_lb["load_balancer"]["forwarding_rules"][0]["entry_port"] == 80
                )
                assert new_lb["load_balancer"]["health_check"]["protocol"] == "http"
                assert new_lb["load_balancer"]["health_check"]["port"] == 80

                # Update the load balancer customizing the health check
                updated_lb = integration_client.load_balancers.update(
                    lb_id=lbid,
                    body={
                        "name": lb_name,
                        "region": defaults.REGION,
                        "forwarding_rules": [
                            {
                                "entry_protocol": "tcp",
                                "entry_port": 80,
                                "target_protocol": "tcp",
                                "target_port": 8080,
                            }
                        ],
                        "tag": tag_name,
                        "health_check": {
                            "protocol": "http",
                            "port": 8080,
                            "path": "/",
                            "check_interval_seconds": 10,
                            "response_timeout_seconds": 5,
                            "healthy_threshold": 5,
                            "unhealthy_threshold": 3,
                        },
                    },
                )
                assert (
                    updated_lb["load_balancer"]["forwarding_rules"][0]["target_port"]
                    == 8080
                )
                assert updated_lb["load_balancer"]["health_check"]["port"] == 8080

                # Add a forwarding rule using the forwarding_rules endpoint
                rule = {
                    "forwarding_rules": [
                        {
                            "entry_protocol": "udp",
                            "entry_port": 194,
                            "target_protocol": "udp",
                            "target_port": 194,
                        }
                    ]
                }
                integration_client.load_balancers.add_forwarding_rules(
                    lb_id=lbid, body=rule
                )
                got_lb = integration_client.load_balancers.get(lb_id=lbid)
                assert len(got_lb["load_balancer"]["forwarding_rules"]) == 2
                assert (
                    got_lb["load_balancer"]["forwarding_rules"][1]["entry_protocol"]
                    == "udp"
                )
                assert (
                    got_lb["load_balancer"]["forwarding_rules"][1]["entry_port"] == 194
                )
                assert (
                    got_lb["load_balancer"]["forwarding_rules"][1]["target_protocol"]
                    == "udp"
                )
                assert (
                    got_lb["load_balancer"]["forwarding_rules"][1]["target_port"] == 194
                )

                # Remove a forwarding rule using the forwarding_rules endpoint
                integration_client.load_balancers.remove_forwarding_rules(
                    lb_id=lbid, body=rule
                )
                got_lb = integration_client.load_balancers.get(lb_id=lbid)
                assert len(got_lb["load_balancer"]["forwarding_rules"]) == 1
                assert (
                    got_lb["load_balancer"]["forwarding_rules"][0]["entry_protocol"]
                    == "tcp"
                )
                assert (
                    got_lb["load_balancer"]["forwarding_rules"][0]["entry_port"] == 80
                )
                assert (
                    got_lb["load_balancer"]["forwarding_rules"][0]["target_protocol"]
                    == "tcp"
                )
                assert (
                    got_lb["load_balancer"]["forwarding_rules"][0]["entry_port"] == 80
                )


def test_load_balancers_droplets(integration_client: Client, public_key: bytes):
    """
    Tests creating a load balancer exercising the add and remove Droplet
    endpoints.
    """
    tag_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
    droplet_req = {
        "name": f"{defaults.PREFIX}-{uuid.uuid4()}",
        "region": defaults.REGION,
        "size": defaults.DROPLET_SIZE,
        "image": defaults.DROPLET_IMAGE,
        "tags": [tag_name],
    }

    with shared.with_test_tag(integration_client, **{"name": tag_name}):
        with shared.with_test_droplet(
            integration_client, public_key, **droplet_req
        ) as droplet:
            # Ensure Droplet create is finished before proceeding
            shared.wait_for_action(
                integration_client, droplet["links"]["actions"][0]["id"]
            )

            lb_name = f"{defaults.PREFIX}-{uuid.uuid4()}"
            lb_create = {
                "name": lb_name,
                "region": defaults.REGION,
                "forwarding_rules": [
                    {
                        "entry_protocol": "tcp",
                        "entry_port": 80,
                        "target_protocol": "tcp",
                        "target_port": 80,
                    }
                ],
            }

            with shared.with_test_load_balancer(
                integration_client, wait=True, body=lb_create
            ) as new_lb:
                lbid = new_lb["load_balancer"]["id"]
                assert lbid is not None
                assert new_lb["load_balancer"]["name"] == lb_name
                assert new_lb["load_balancer"]["tag"] == ""
                assert new_lb["load_balancer"]["droplet_ids"] == []

                # Add Droplet
                droplet_ids = {"droplet_ids": [droplet["droplet"]["id"]]}
                integration_client.load_balancers.add_droplets(
                    lb_id=lbid, body=droplet_ids
                )
                got_lb = integration_client.load_balancers.get(lb_id=lbid)
                assert got_lb["load_balancer"]["droplet_ids"] == [
                    droplet["droplet"]["id"]
                ]

                # Remove Droplet
                integration_client.load_balancers.remove_droplets(
                    lb_id=lbid, body=droplet_ids
                )
                got_lb = integration_client.load_balancers.get(lb_id=lbid)
                assert got_lb["load_balancer"]["droplet_ids"] == []
