"""Test data for kubernetes requests"""

# pylint: disable=line-too-long

CLUSTER = {
    "kubernetes_cluster": {
        "id": "bd5f5959-5e1e-4205-a714-a914373942af",
        "name": "prod-cluster-01",
        "region": "nyc1",
        "version": "1.18.6-do.0",
        "cluster_subnet": "10.244.0.0/16",
        "service_subnet": "10.245.0.0/16",
        "vpc_uuid": "c33931f2-a26a-4e61-b85c-4e95a2ec431b",
        "ipv4": "",
        "endpoint": "",
        "tags": ["k8s", "k8s:bd5f5959-5e1e-4205-a714-a914373942af"],
        "node_pools": [
            {
                "id": "cdda885e-7663-40c8-bc74-3a036c66545d",
                "name": "worker-pool",
                "size": "s-1vcpu-2gb",
                "count": 3,
                "tags": [
                    "k8s",
                    "k8s:bd5f5959-5e1e-4205-a714-a914373942af",
                    "k8s:worker",
                ],
                "labels": None,
                "taints": [],
                "auto_scale": False,
                "min_nodes": 0,
                "max_nodes": 0,
                "nodes": [
                    {
                        "id": "478247f8-b1bb-4f7a-8db9-2a5f8d4b8f8f",
                        "name": "",
                        "status": {"state": "provisioning"},
                        "droplet_id": "",
                        "created_at": "2018-11-15T16:00:11.000Z",
                        "updated_at": "2018-11-15T16:00:11.000Z",
                    },
                    {
                        "id": "ad12e744-c2a9-473d-8aa9-be5680500eb1",
                        "name": "",
                        "status": {"state": "provisioning"},
                        "droplet_id": "",
                        "created_at": "2018-11-15T16:00:11.000Z",
                        "updated_at": "2018-11-15T16:00:11.000Z",
                    },
                    {
                        "id": "e46e8d07-f58f-4ff1-9737-97246364400e",
                        "name": "",
                        "status": {"state": "provisioning"},
                        "droplet_id": "",
                        "created_at": "2018-11-15T16:00:11.000Z",
                        "updated_at": "2018-11-15T16:00:11.000Z",
                    },
                ],
            }
        ],
        "maintenance_policy": {
            "start_time": "00:00",
            "duration": "4h0m0s",
            "day": "any",
        },
        "auto_upgrade": False,
        "status": {"state": "provisioning", "message": "provisioning"},
        "created_at": "2018-11-15T16:00:11.000Z",
        "updated_at": "2018-11-15T16:00:11.000Z",
        "surge_upgrade": False,
        "registry_enabled": False,
        "ha": False,
    }
}

ASSOCIATED_RESOURCES = {
    "load_balancers": [
        {"id": "4de7ac8b-495b-4884-9a69-1050c6793cd6", "name": "lb-001"}
    ],
    "volumes": [{"id": "ba49449a-7435-11ea-b89e-0a58ac14480f", "name": "volume-001"}],
    "volume_snapshots": [
        {"id": "edb0478d-7436-11ea-86e6-0a58ac144b91", "name": "snapshot-001"}
    ],
}

KUBECONFIG = """apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSURUxCUUF3TXpFVk1CTUdBMVVFQ2ftTVJHbG4KYVhSaGJFOWpaV0Z1TVJvd0dUSREERXhGck9ITmhZWE1nUTJ4MWMzUmxjaUJEUVRBZUZ3MHhPREV4TVRVeApOakF3TWpCYUZ3MHpPREV4TVRVeE5qQXdNakJhTURNeEZUQVRCZ05WQkFvVERFUnBaMmwwWVd4UFkyVmhiakVhCk1CZ0dBMVVFQXhNUmF6aHpZV0Z6SUVOc2RYTjBaWElnUTBFd2dnRWlNQTBHQ1NxR1NJYjNEUUVCQVFVQUE0SUIKRHdBd2dnRUtBb0lCQVFDK2Z0L05Nd3pNaUxFZlFvTFU2bDgrY0hMbWttZFVKdjl4SmlhZUpIU0dZOGhPZFVEZQpGd1Zoc0pDTnVFWkpJUFh5Y0orcGpkU3pYc1lFSE03WVNKWk9xNkdaYThPMnZHUlJjN2ZQaUFJaFBRK0ZpUmYzCmRhMHNIUkZlM2hCTmU5ZE5SeTliQ2VCSTRSUlQrSEwzRFR3L2I5KytmRkdZQkRoVTEvTTZUWWRhUHR3WU0rdWgKb1pKcWJZVGJZZTFhb3R1ekdnYUpXaXRhdFdHdnNJYU8xYWthdkh0WEIOOHFxa2lPemdrSDdvd3RVY3JYM05iawozdmlVeFU4TW40MmlJaGFyeHNvTnlwdGhHOWZLMi9OdVdKTXJJS2R0Mzhwc0tkdDBFbng0MWg5K0dsMjUzMzhWCk1mdjBDVDF6SG1JanYwblIrakNkcFd0eFVLRyt0YjYzZFhNbkFnTUJBQUdqUlRCRE1BNEdBMVVkRHdFQi93UUUKQXdJQmhqQVNCZ05WSFJNQkFmOEVDREFHQVFIL0FnRUFNQjBHQTFVZERnUVdCQlNQMmJrOXJiUGJpQnZOd1Z1NQpUL0dwTFdvOTdEQU5CZ2txaGtpRzl3MEJBUXNGQUFPQ0FRRUFEVjFMSGZyc1JiYVdONHE5SnBFVDMxMlluRDZ6Cm5rM3BpU1ZSYVEvM09qWG8wdHJ6Z2N4KzlVTUQxeDRHODI1RnYxc0ROWUExZEhFc2dHUmNyRkVmdGZJQWUrUVYKTitOR3NMRnQrOGZrWHdnUlpoNEU4ZUJsSVlrdEprOWptMzFMT25vaDJYZno0aGs3VmZwYkdvVVlsbmVoak1JZApiL3ZMUk05Y2EwVTJlYTB5OTNveE5pdU9PcXdrZGFjU1orczJtb3JNdGZxc3VRSzRKZDA3SENIbUFIeWpXT2k4ClVOQVUyTnZnSnBKY2RiZ3VzN2I5S3ppR1ZERklFUk04cEo4U1Nob1ZvVFFJd3d5Y2xVTU9EUUJreFFHOHNVRk8KRDE3ZjRod1dNbW5qVHY2MEJBM0dxaTZRcjdsWVFSL3drSEtQcnZjMjhoNXB0NndPWEY1b1M4OUZkUT09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K
    server: https://bd5f5959-5e1e-4205-a714-a914373942af.k8s.ondigitalocean.com
  name: do-nyc1-prod-cluster-01
contexts:
- context:
    cluster: do-nyc1-prod-cluster-01
    user: do-nyc1-prod-cluster-01-admin
  name: do-nyc1-prod-cluster-01
current-context: do-nyc1-prod-cluster-01
kind: Config
preferences: {}
users:
- name: do-nyc1-prod-cluster-01-admin
  user:
    token: 403d085aaa80102277d8da97ffd2db2b6a4f129d0e2146098fdfb0cec624babc
"""

CREDENTIALS = {
    "server": "https://bd5f5959-5e1e-4205-a714-a914373942af.k8s.ondigitalocean.com",
    "certificate_authority_data": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSURKekNDQWcrZ0F3SUJBZ0lDQm5Vd0RRWUpLb1pJaHZjTkFRRUxCUUF3TXpFVk1CTUdBMVVFQ2hNTVJHbG4KYVhSaGJFOWpaV0Z1TVJvd0dBWURWUVFERXhGck9ITmhZWE1nUTJ4MWMzUmxjaUJEUVRBZUZ3MHlNREE0TURNeApOVEkxTWpoYUZ3MDBNREE0TURNeE5USTFNamhhTURNeEZUQVRCZ05WQkFvVERFUnBaMmwwWVd4UFkyVmhiakVhCk1CZ0dBMVVFQXhNUmF6aHpZV0Z6SUVOc2RYTjBaWElnUTBFd2dnRWlNQTBHQ1NxR1NJYjNEUUVCQVFVQUE0SUIKRHdBd2dnRUtBb0lCQVFDc21oa2JrSEpUcGhZQlN0R05VVE1ORVZTd2N3bmRtajArelQvcUZaNGsrOVNxUnYrSgpBd0lCaGpBU0JnTlZIUk1CQWY4RUNEQUdBUUgvQWdFQU1CMEdBMVVkRGdRV0JCUlRzazhhZ1hCUnFyZXdlTXJxClhwa3E1NXg5dVRBTkJna3Foa2lHOXcwQkFRc0ZBQU9DQVFFQXB6V2F6bXNqYWxXTEx3ZjVpbWdDblNINDlKcGkKYWkvbzFMdEJvVEpleGdqZzE1ZVppaG5BMUJMc0lWNE9BZGM3UEFsL040L0hlbENrTDVxandjamRnNVdaYnMzYwozcFVUQ0g5bVVwMFg1SVdhT1VKV292Q1hGUlM1R2VKYXlkSDVPUXhqTURzR2N2UlNvZGQrVnQ2MXE3aWdFZ2I1CjBOZ1l5RnRnc2p0MHpJN3hURzZFNnlsOVYvUmFoS3lIQks2eExlM1RnUGU4SXhWa2RwT3QzR0FhSDRaK0pLR3gKYisyMVZia1NnRE1QQTlyR0VKNVZwVXlBV0FEVXZDRVFHV0hmNGpQN2ZGZlc3T050S0JWY3h3YWFjcVBVdUhzWApwRG5DZVR3V1NuUVp6L05xNmQxWUtsMFdtbkwzTEowemJzRVFGbEQ4MkkwL09MY2dZSDVxMklOZHhBPT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=",
    "client_certificate_data": None,
    "client_key_data": None,
    "token": "$DIGITALOCEAN_TOKEN",
    "expires_at": "2019-11-09T11:50:28.889080521Z",
}

AVAILABLE_UPGRADES = {
    "available_upgrade_versions": [
        {
            "slug": "1.16.13-do.0",
            "kubernetes_version": "1.16.13",
            "supported_features": [
                "cluster-autoscaler",
                "docr-integration",
                "token-authentication",
            ],
        }
    ]
}

NODE_POOL = {
    "node_pool": {
        "id": "cdda885e-7663-40c8-bc74-3a036c66545d",
        "name": "new-pool",
        "size": "s-1vcpu-2gb",
        "count": 3,
        "tags": [
            "production",
            "web-team",
            "front-end",
            "k8s",
            "k8s:bd5f5959-5e1e-4205-a714-a914373942af",
            "k8s:worker",
        ],
        "labels": None,
        "taints": [],
        "auto_scale": True,
        "min_nodes": 3,
        "max_nodes": 6,
        "nodes": [
            {
                "id": "478247f8-b1bb-4f7a-8db9-2a5f8d4b8f8f",
                "name": " ",
                "status": {"state": "provisioning"},
                "droplet_id": " ",
                "created_at": "2018-11-15T16:00:11Z",
                "updated_at": "2018-11-15T16:00:11Z",
            },
            {
                "id": "ad12e744-c2a9-473d-8aa9-be5680500eb1",
                "name": " ",
                "status": {"state": "provisioning"},
                "droplet_id": " ",
                "created_at": "2018-11-15T16:00:11Z",
                "updated_at": "2018-11-15T16:00:11Z",
            },
            {
                "id": "e46e8d07-f58f-4ff1-9737-97246364400e",
                "name": " ",
                "status": {"state": "provisioning"},
                "droplet_id": " ",
                "created_at": "2018-11-15T16:00:11Z",
                "updated_at": "2018-11-15T16:00:11Z",
            },
        ],
    }
}

NODE_POOLS = {
    "node_pools": [
        {
            "id": "cdda885e-7663-40c8-bc74-3a036c66545d",
            "name": "frontend-pool",
            "size": "s-1vcpu-2gb",
            "count": 3,
            "tags": [
                "production",
                "web-team",
                "k8s",
                "k8s:bd5f5959-5e1e-4205-a714-a914373942af",
                "k8s:worker",
            ],
            "labels": None,
            "auto_scale": False,
            "min_nodes": 0,
            "max_nodes": 0,
            "nodes": [
                {
                    "id": "478247f8-b1bb-4f7a-8db9-2a5f8d4b8f8f",
                    "name": "adoring-newton-3niq",
                    "status": {"state": "running"},
                    "droplet_id": "205545370",
                    "created_at": "2018-11-15T16:00:11Z",
                    "updated_at": "2018-11-15T16:00:11Z",
                },
                {
                    "id": "ad12e744-c2a9-473d-8aa9-be5680500eb1",
                    "name": "adoring-newton-3nim",
                    "status": {"state": "running"},
                    "droplet_id": "205545371",
                    "created_at": "2018-11-15T16:00:11Z",
                    "updated_at": "2018-11-15T16:00:11Z",
                },
                {
                    "id": "e46e8d07-f58f-4ff1-9737-97246364400e",
                    "name": "adoring-newton-3ni7",
                    "status": {"state": "running"},
                    "droplet_id": "205545372",
                    "created_at": "2018-11-15T16:00:11Z",
                    "updated_at": "2018-11-15T16:00:11Z",
                },
            ],
        },
        {
            "id": "f49f4379-7e7f-4af5-aeb6-0354bd840778",
            "name": "backend-pool",
            "size": "g-4vcpu-16gb",
            "count": 2,
            "tags": [
                "production",
                "web-team",
                "k8s",
                "k8s:bd5f5959-5e1e-4205-a714-a914373942af",
                "k8s:worker",
            ],
            "labels": {"service": "backend", "priority": "high"},
            "auto_scale": True,
            "min_nodes": 2,
            "max_nodes": 5,
            "nodes": [
                {
                    "id": "3385619f-8ec3-42ba-bb23-8d21b8ba7518",
                    "name": "affectionate-nightingale-3nif",
                    "status": {"state": "running"},
                    "droplet_id": "205545373",
                    "created_at": "2018-11-15T16:00:11Z",
                    "updated_at": "2018-11-15T16:00:11Z",
                },
                {
                    "id": "4b8f60ff-ba06-4523-a6a4-b8148244c7e6",
                    "name": "affectionate-nightingale-3niy",
                    "status": {"state": "running"},
                    "droplet_id": "205545374",
                    "created_at": "2018-11-15T16:00:11Z",
                    "updated_at": "2018-11-15T16:00:11Z",
                },
            ],
        },
    ]
}

OPTIONS = {
    "options": {
        "regions": [
            {"name": "New York 1", "slug": "nyc1"},
            {"name": "Singapore 1", "slug": "sgp1"},
            {"name": "London 1", "slug": "lon1"},
            {"name": "New York 3", "slug": "nyc3"},
            {"name": "Amsterdam 3", "slug": "ams3"},
            {"name": "Frankfurt 1", "slug": "fra1"},
            {"name": "Toronto 1", "slug": "tor1"},
            {"name": "San Francisco 2", "slug": "sfo2"},
            {"name": "Bangalore 1", "slug": "blr1"},
            {"name": "San Francisco 3", "slug": "sfo3"},
        ],
        "versions": [
            {
                "slug": "1.18.8-do.0",
                "kubernetes_version": "1.18.8",
                "supported_features": [
                    "cluster-autoscaler",
                    "docr-integration",
                    "token-authentication",
                ],
            },
            {
                "slug": "1.17.11-do.0",
                "kubernetes_version": "1.17.11",
                "supported_features": [
                    "cluster-autoscaler",
                    "docr-integration",
                    "token-authentication",
                ],
            },
            {
                "slug": "1.16.14-do.0",
                "kubernetes_version": "1.16.14",
                "supported_features": [
                    "cluster-autoscaler",
                    "docr-integration",
                    "token-authentication",
                ],
            },
        ],
        "sizes": [
            {"name": "s-1vcpu-2gb", "slug": "s-1vcpu-2gb"},
            {"name": "s-2vcpu-2gb", "slug": "s-2vcpu-2gb"},
            {"name": "s-1vcpu-3gb", "slug": "s-1vcpu-3gb"},
            {"name": "s-2vcpu-4gb", "slug": "s-2vcpu-4gb"},
            {"name": "s-4vcpu-8gb", "slug": "s-4vcpu-8gb"},
            {"name": "c-2-4GiB", "slug": "c-2"},
            {"name": "g-2vcpu-8gb", "slug": "g-2vcpu-8gb"},
            {"name": "gd-2vcpu-8gb", "slug": "gd-2vcpu-8gb"},
            {"name": "s-8vcpu-16gb", "slug": "s-8vcpu-16gb"},
            {"name": "s-6vcpu-16gb", "slug": "s-6vcpu-16gb"},
            {"name": "c-4-8GiB", "slug": "c-4"},
            {"name": "m-2vcpu-16gb", "slug": "m-2vcpu-16gb"},
            {"name": "m3-2vcpu-16gb", "slug": "m3-2vcpu-16gb"},
            {"name": "g-4vcpu-16gb", "slug": "g-4vcpu-16gb"},
            {"name": "gd-4vcpu-16gb", "slug": "gd-4vcpu-16gb"},
            {"name": "m6-2vcpu-16gb", "slug": "m6-2vcpu-16gb"},
            {"name": "s-8vcpu-32gb", "slug": "s-8vcpu-32gb"},
            {"name": "c-8-16GiB", "slug": "c-8"},
            {"name": "m-4vcpu-32gb", "slug": "m-4vcpu-32gb"},
            {"name": "m3-4vcpu-32gb", "slug": "m3-4vcpu-32gb"},
            {"name": "g-8vcpu-32gb", "slug": "g-8vcpu-32gb"},
            {"name": "s-12vcpu-48gb", "slug": "s-12vcpu-48gb"},
            {"name": "gd-8vcpu-32gb", "slug": "gd-8vcpu-32gb"},
            {"name": "m6-4vcpu-32gb", "slug": "m6-4vcpu-32gb"},
            {"name": "s-16vcpu-64gb", "slug": "s-16vcpu-64gb"},
            {"name": "c-16", "slug": "c-16"},
            {"name": "m-8vcpu-64gb", "slug": "m-8vcpu-64gb"},
            {"name": "m3-8vcpu-64gb", "slug": "m3-8vcpu-64gb"},
            {"name": "g-16vcpu-64gb", "slug": "g-16vcpu-64gb"},
            {"name": "s-20vcpu-96gb", "slug": "s-20vcpu-96gb"},
            {"name": "gd-16vcpu-64gb", "slug": "gd-16vcpu-64gb"},
            {"name": "m6-8vcpu-64gb", "slug": "m6-8vcpu-64gb"},
            {"name": "s-24vcpu-128gb", "slug": "s-24vcpu-128gb"},
            {"name": "c-32-64GiB", "slug": "c-32"},
            {"name": "m-16vcpu-128gb", "slug": "m-16vcpu-128gb"},
            {"name": "m3-16vcpu-128gb", "slug": "m3-16vcpu-128gb"},
            {"name": "g-32vcpu-128gb", "slug": "g-32vcpu-128gb"},
            {"name": "s-32vcpu-192gb", "slug": "s-32vcpu-192gb"},
            {"name": "gd-32vcpu-128gb", "slug": "gd-32vcpu-128gb"},
            {"name": "m-24vcpu-192gb", "slug": "m-24vcpu-192gb"},
            {"name": "m6-16vcpu-128gb", "slug": "m6-16vcpu-128gb"},
            {"name": "g-40vcpu-160gb", "slug": "g-40vcpu-160gb"},
            {"name": "gd-40vcpu-160gb", "slug": "gd-40vcpu-160gb"},
            {"name": "m3-24vcpu-192gb", "slug": "m3-24vcpu-192gb"},
            {"name": "m-32vcpu-256gb", "slug": "m-32vcpu-256gb"},
            {"name": "m6-24vcpu-192gb", "slug": "m6-24vcpu-192gb"},
            {"name": "m3-32vcpu-256gb", "slug": "m3-32vcpu-256gb"},
            {"name": "m6-32vcpu-256gb", "slug": "m6-32vcpu-256gb"},
        ],
    }
}

CLUSTER_LINT = {
    "run_id": "50c2f44c-011d-493e-aee5-361a4a0d1844",
    "requested_at": "2019-10-30T05:34:07Z",
    "completed_at": "2019-10-30T05:34:11Z",
    "diagnostics": [
        {
            "check_name": "unused-config-map",
            "severity": "warning",
            "message": "Unused config map",
            "object": {"name": "foo", "kind": "config map", "namespace": "kube-system"},
        }
    ],
}
