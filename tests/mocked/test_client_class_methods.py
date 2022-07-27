""" Tests the base generated client."""

import pytest


@pytest.fixture(scope="module")
def client_resources(mock_client):
    """Module fixture to get the list of members of the generated client.

    Only public members are returned and the base client methods are
    excluded.
    """
    exclude_members = ["close", "send_request"]
    resources = {
        r: {}
        for r in dir(mock_client)
        if "__" not in r and r[0] != "_" and r not in exclude_members
    }

    for res in resources:
        res_methods = getattr(mock_client, res)
        resources[res] = {
            op for op in dir(res_methods) if "__" not in op and op[0] != "_"
        }

    return resources


# pylint: disable=redefined-outer-name
def test_class_names(client_resources):
    """Tests that the generated classes match known API resources."""
    expect = [
        "account",
        "actions",
        "apps",
        "balance",
        "billing_history",
        "cdn",
        "certificates",
        "databases",
        "domains",
        "droplet_actions",
        "droplets",
        "firewalls",
        "image_actions",
        "images",
        "invoices",
        "kubernetes",
        "load_balancers",
        "monitoring",
        "one_clicks",
        "projects",
        "regions",
        "registry",
        "reserved_ips",
        "reserved_ips_actions",
        "sizes",
        "snapshots",
        "ssh_keys",
        "tags",
        "volume_actions",
        "volume_snapshots",
        "volumes",
        "vpcs",
    ]

    assert set(client_resources.keys()) == set(expect)


@pytest.mark.parametrize(
    "group,operations,patched_methods",
    [
        ("account", {"get"}, {}),
        ("actions", {"get", "list"}, {}),
        (
            "apps",
            {
                "get_tier",
                "list_instance_sizes",
                "validate_app_spec",
                "list_alerts",
                "cancel_deployment",
                "get_logs_aggregate",
                "create_rollback",
                "update",
                "get_logs",
                "list_tiers",
                "list_regions",
                "create",
                "get_deployment",
                "revert_rollback",
                "list_deployments",
                "create_deployment",
                "validate_rollback",
                "list",
                "get",
                "commit_rollback",
                "get_instance_size",
                "assign_alert_destinations",
                "delete",
            },
            {},
        ),
        ("balance", {"get"}, {}),
        ("billing_history", {"list"}, {}),
        (
            "cdn",
            {
                "delete_endpoint",
                "purge_cache",
                "create_endpoint",
                "list_endpoints",
                "update_endpoints",
                "get_endpoint",
            },
            {},
        ),
        ("certificates", {"get", "delete", "list", "create"}, {}),
        (
            "databases",
            {
                "add_connection_pool",
                "update_eviction_policy",
                "list_backups",
                "list_clusters",
                "update_region",
                "create_cluster",
                "get_ca",
                "update_sql_mode",
                "add_user",
                "delete_online_migration",
                "reset_auth",
                "get_cluster",
                "destroy_replica",
                "get_connection_pool",
                "get_replica",
                "list_connection_pools",
                "update_cluster_size",
                "delete_user",
                "get_config",
                "patch_config",
                "update_firewall_rules",
                "delete_connection_pool",
                "get_migration_status",
                "update_maintenance_window",
                "update_online_migration",
                "get_eviction_policy",
                "create_replica",
                "list_users",
                "list",
                "get",
                "list_firewall_rules",
                "list_replicas",
                "delete",
                "get_sql_mode",
                "get_user",
                "add",
                "destroy_cluster",
            },
            {},
        ),
        (
            "domains",
            {
                "list_records",
                "list",
                "create",
                "get_record",
                "get",
                "patch_record",
                "update_record",
                "create_record",
                "delete",
                "delete_record",
            },
            {},
        ),
        ("droplet_actions", {"get", "post_by_tag", "post", "list"}, {}),
        (
            "droplets",
            {
                "list_neighbors_ids",
                "destroy_with_associated_resources_selective",
                "list_kernels",
                "destroy_retry_with_associated_resources",
                "create",
                "list",
                "get",
                "get_destroy_associated_resources_status",
                "list_firewalls",
                "list_neighbors",
                "destroy",
                "list_backups",
                "destroy_with_associated_resources_dangerous",
                "destroy_by_tag",
                "list_snapshots",
                "list_associated_resources",
            },
            {},
        ),
        (
            "firewalls",
            {
                "add_tags",
                "list",
                "create",
                "get",
                "delete_rules",
                "update",
                "delete_droplets",
                "add_rules",
                "delete",
                "assign_droplets",
                "delete_tags",
            },
            {},
        ),
        ("image_actions", {"get", "post", "list"}, {}),
        ("images", {"list", "get", "update", "create_custom", "delete"}, {}),
        (
            "invoices",
            {
                "list",
                "get_summary_by_uuid",
                "get_pdf_by_uuid",
                "get_csv_by_uuid",
                "get_by_uuid",
            },
            {},
        ),
        (
            "kubernetes",
            {
                "delete_node",
                "list_clusters",
                "destroy_associated_resources_dangerous",
                "upgrade_cluster",
                "create_cluster",
                "update_node_pool",
                "delete_node_pool",
                "remove_registry",
                "get_cluster",
                "get_cluster_user",
                "run_cluster_lint",
                "add_node_pool",
                "update_cluster",
                "get_available_upgrades",
                "destroy_associated_resources_selective",
                "get_node_pool",
                "list_associated_resources",
                "get_kubeconfig",
                "get_cluster_lint_results",
                "list_options",
                "list_node_pools",
                "delete_cluster",
                "recycle_node_pool",
                "get_credentials",
                "add_registry",
            },
            {},
        ),
        (
            "load_balancers",
            {
                "add_forwarding_rules",
                "list",
                "create",
                "get",
                "update",
                "remove_droplets",
                "delete",
                "add_droplets",
                "remove_forwarding_rules",
            },
            {},
        ),
        (
            "monitoring",
            {
                "get_alert_policy",
                "get_droplet_memory_free_metrics",
                "delete_alert_policy",
                "get_droplet_filesystem_size_metrics",
                "get_droplet_memory_cached_metrics",
                "create_alert_policy",
                "list_alert_policy",
                "get_droplet_bandwidth_metrics",
                "get_droplet_load1_metrics",
                "get_droplet_filesystem_free_metrics",
                "get_droplet_memory_total_metrics",
                "get_droplet_load5_metrics",
                "get_droplet_memory_available_metrics",
                "get_droplet_load15_metrics",
                "get_droplet_cpu_metrics",
                "update_alert_policy",
            },
            {},
        ),
        ("one_clicks", {"install_kubernetes", "list"}, {}),
        (
            "projects",
            {
                "list",
                "create",
                "get_default",
                "get",
                "assign_resources",
                "patch",
                "update",
                "assign_resources_default",
                "update_default",
                "list_resources_default",
                "delete",
                "list_resources",
                "patch_default",
            },
            {},
        ),
        ("regions", {"list"}, {}),
        (
            "registry",
            {
                "list_repository_tags",
                "update_subscription",
                "delete_repository_manifest",
                "create",
                "get",
                "get_options",
                "run_garbage_collection",
                "get_subscription",
                "update_garbage_collection",
                "get_garbage_collection",
                "list_repository_manifests",
                "delete",
                "list_garbage_collections",
                "list_repositories",
                "validate_name",
                "get_docker_credentials",
                "delete_repository_tag",
                "list_repositories_v2",
            },
            {},
        ),
        ("reserved_ips", {"get", "delete", "list", "create"}, {}),
        ("reserved_ips_actions", {"get", "post", "list"}, {}),
        ("sizes", {"list"}, {}),
        ("snapshots", {"get", "list", "delete"}, {}),
        ("ssh_keys", {"list", "create", "get", "update", "delete"}, {}),
        (
            "tags",
            {
                "list",
                "create",
                "get",
                "assign_resources",
                "delete",
                "unassign_resources",
            },
            {},
        ),
        (
            "volume_actions",
            {"list", "get", "post", "post_by_id"},
            {},
        ),
        ("volume_snapshots", {"get_by_id", "delete_by_id", "list", "create"}, {}),
        ("volumes", {"list", "create", "get", "delete", "delete_by_name"}, {}),
        (
            "vpcs",
            {"list", "create", "get", "patch", "update", "list_members", "delete"},
            {},
        ),
    ],
)
def test_resource_class_operations(
    client_resources, group, operations, patched_methods
):
    """Checks that the classes on the generated client have the expected
    methods for the respective operations.

    The parameterized inputs provide:
    * group (str): name of the resource
    * operations (set): a set of expected method names
    * patched_methods (set): a set of methods added via _patch.py

    If a set of patched_methods is provided, we expect the difference
    between operations and class_methods to be the set provided in
    patched_methods.
    """
    class_methods = client_resources[group]
    if patched_methods and len(patched_methods) > 0:
        assert class_methods - operations == patched_methods
    else:
        assert class_methods == operations
