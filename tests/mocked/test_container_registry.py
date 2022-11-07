# pylint: disable=duplicate-code,line-too-long
"""Mock tests for container registry API resource"""

import responses

from pydo import Client


@responses.activate
def test_container_registry_create(mock_client: Client, mock_client_url):
    """Tests Container Registry Creation"""
    expected = {
        "registry": {
            "name": "example",
            "created_at": "2020-03-21T16:02:37Z",
            "region": "fra1",
            "storage_usage_bytes": 29393920,
            "storage_usage_bytes_updated_at": "2020-11-04T21:39:49.530562231Z",
            "subscription": {
                "tier": {
                    "name": "Basic",
                    "slug": "basic",
                    "included_repositories": 5,
                    "included_storage_bytes": 5368709120,
                    "allow_storage_overage": True,
                    "included_bandwidth_bytes": 5368709120,
                    "monthly_price_in_cents": 500,
                    "storage_overage_price_in_cents": 2,
                },
                "created_at": "2020-01-23T21:19:12Z",
                "updated_at": "2020-11-05T15:53:24Z",
            },
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/registry",
        json=expected,
        status=201,
    )

    create_resp = mock_client.registry.create(
        {"name": "example", "subscription_tier_slug": "basic", "region": "fra1"}
    )

    assert create_resp == expected


@responses.activate
def test_container_registry_get(mock_client: Client, mock_client_url):
    """Test Container Registry"""
    expected = {
        "registry": {
            "name": "example",
            "created_at": "2020-03-21T16:02:37Z",
            "region": "fra1",
            "storage_usage_bytes": 29393920,
            "storage_usage_bytes_updated_at": "2020-11-04T21:39:49.530562231Z",
            "subscription": {
                "tier": {
                    "name": "Basic",
                    "slug": "basic",
                    "included_repositories": 5,
                    "included_storage_bytes": 5368709120,
                    "allow_storage_overage": True,
                    "included_bandwidth_bytes": 5368709120,
                    "monthly_price_in_cents": 500,
                    "storage_overage_price_in_cents": 2,
                },
                "created_at": "2020-01-23T21:19:12Z",
                "updated_at": "2020-11-05T15:53:24Z",
            },
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/registry",
        json=expected,
        status=200,
    )

    get_resp = mock_client.registry.get()

    assert get_resp == expected


@responses.activate
def test_container_registry_delete(mock_client: Client, mock_client_url):
    """Test Container Registry Delete"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/registry",
        status=204,
    )
    del_resp = mock_client.registry.delete()

    assert del_resp is None


@responses.activate
def test_container_registry_get_subscription_info(mock_client: Client, mock_client_url):
    """Test Container Registry Get Subscription Info"""
    expected = {
        "subscription": {
            "tier": {
                "name": "Basic",
                "slug": "basic",
                "included_repositories": 5,
                "included_storage_bytes": 5368709120,
                "allow_storage_overage": True,
                "included_bandwidth_bytes": 5368709120,
                "monthly_price_in_cents": 500,
                "storage_overage_price_in_cents": 2,
            },
            "created_at": "2020-01-23T21:19:12Z",
            "updated_at": "2020-11-05T15:53:24Z",
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/registry/subscription",
        json=expected,
        status=200,
    )

    get_resp = mock_client.registry.get_subscription()

    assert get_resp == expected


@responses.activate
def test_container_registry_update_subscription(mock_client: Client, mock_client_url):
    """Test Container Registry Update Subscription"""
    expected = {
        "subscription": {
            "tier": {
                "name": "Basic",
                "slug": "basic",
                "included_repositories": 5,
                "included_storage_bytes": 5368709120,
                "allow_storage_overage": True,
                "included_bandwidth_bytes": 5368709120,
                "monthly_price_in_cents": 500,
                "storage_overage_price_in_cents": 2,
            },
            "created_at": "2020-01-23T21:19:12Z",
            "updated_at": "2020-11-05T15:53:24Z",
        }
    }

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/registry/subscription",
        json=expected,
        status=200,
    )

    update_resp = mock_client.registry.update_subscription(body={"tier_slug": "basic"})

    assert update_resp == expected


@responses.activate
def test_container_registry_get_docker_creds(mock_client: Client, mock_client_url):
    """Test Docker Creds"""
    expected = {
        "auths": {
            "registry.digitalocean.com": {"auth": "YjdkMDNhNjk0N2IyMZDM1MDQ1ODIK"}
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/registry/docker-credentials",
        json=expected,
        status=200,
    )

    get_resp = mock_client.registry.get_docker_credentials()

    assert get_resp == expected


@responses.activate
def test_container_registry_validate_name(mock_client: Client, mock_client_url):
    """Tests Container Registry Validate Name"""
    expected = None

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/registry/validate-name",
        json=expected,
        status=204,
    )

    create_resp = mock_client.registry.validate_name({"name": "example"})

    assert create_resp == expected


@responses.activate
def test_container_registry_list_repositories(mock_client: Client, mock_client_url):
    """Test Container Registry's list repositories endpoint"""
    expected = {
        "repositories": [
            {
                "registry_name": "example",
                "name": "repo-1",
                "tag_count": 57,
                "manifest_count": 82,
                "latest_manifest": {
                    "digest": "sha256:cb8a924afdf0229ef7515d9e5b3024e23b3eb03ddbba287f4a19c6ac90b8d221",
                    "registry_name": "example",
                    "repository": "repo-1",
                    "compressed_size_bytes": 1972332,
                    "size_bytes": 2816445,
                    "updated_at": "2021-04-09T23:54:25Z",
                    "tags": ["v1", "v2"],
                    "blobs": [
                        {
                            "digest": "sha256:14119a10abf4669e8cdbdff324a9f9605d99697215a0d21c360fe8dfa8471bab",
                            "compressed_size_bytes": 1471,
                        },
                        {
                            "digest": "sha256:a0d0a0d46f8b52473982a3c466318f479767577551a53ffc9074c9fa7035982e",
                            "compressed_size_byte": 2814446,
                        },
                        {
                            "digest": "sha256:69704ef328d05a9f806b6b8502915e6a0a4faa4d72018dc42343f511490daf8a",
                            "compressed_size_bytes": 528,
                        },
                    ],
                },
            }
        ],
        "meta": {"total": 5},
        "links": {
            "pages": {
                "next": "https://api.digitalocean.com/v2/registry/example/repositoriesV2?page=2&page_token=JPZmZzZXQiOjB9&per_page=1",
                "last": "https://api.digitalocean.com/v2/registry/example/repositoriesV2?page=5&per_page=1",
            }
        },
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/registry/example/repositoriesV2",
        json=expected,
        status=200,
    )

    get_resp = mock_client.registry.list_repositories_v2(registry_name="example")

    assert get_resp == expected


@responses.activate
def test_container_registry_list_repositories_tags(
    mock_client: Client, mock_client_url
):
    """Test Container Registry's list repositories tags endpoint"""
    expected = {
        "tags": [
            {
                "registry_name": "example",
                "repository": "repo-1",
                "tag": "latest",
                "manifest_digest": "sha256:cb8a924afdf0229ef7515d9e5b3024e23b3eb03ddbba287f4a19c6ac90b8d221",
                "compressed_size_bytes": 2803255,
                "size_bytes": 5861888,
                "updated_at": "2020-04-09T23:54:25Z",
            }
        ],
        "meta": {"total": 1},
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/registry/example/repo-1/tags",
        json=expected,
        status=200,
    )

    get_resp = mock_client.registry.list_repository_tags(
        registry_name="example", repository_name="repo-1"
    )

    assert get_resp == expected


@responses.activate
def test_container_registry_tag_delete(mock_client: Client, mock_client_url):
    """Test Container Registry Delete Tag"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/registry/example/repo-1/tags/tag1",
        status=204,
    )
    del_resp = mock_client.registry.delete_repository_tag(
        registry_name="example", repository_name="repo-1", repository_tag="tag1"
    )

    assert del_resp is None


@responses.activate
def test_container_registry_list_repository_manifests(
    mock_client: Client, mock_client_url
):
    """Test Container Registry's list repositories manifests"""
    expected = {
        "manifests": [
            {
                "digest": "sha256:cb8a924afdf0229ef7515d9e5b3024e23b3eb03ddbba287f4a19c6ac90b8d221",
                "registry_name": "example",
                "repository": "repo-1",
                "compressed_size_bytes": 1972332,
                "size_bytes": 2816445,
                "updated_at": "2021-04-09T23:54:25Z",
                "tags": ["v1", "v2"],
                "blobs": [
                    {
                        "digest": "sha256:14119a10abf4669e8cdbdff324a9f9605d99697215a0d21c360fe8dfa8471bab",
                        "compressed_size_bytes": 1471,
                    },
                    {
                        "digest": "sha256:a0d0a0d46f8b52473982a3c466318f479767577551a53ffc9074c9fa7035982e",
                        "compressed_size_byte": 2814446,
                    },
                    {
                        "digest": "sha256:69704ef328d05a9f806b6b8502915e6a0a4faa4d72018dc42343f511490daf8a",
                        "compressed_size_bytes": 528,
                    },
                ],
            }
        ],
        "meta": {"total": 3},
        "links": {
            "pages": {
                "first": "https://api.digitalocean.com/v2/registry/example/repositories/repo-1/digests?page=1&per_page=1",
                "prev": "https://api.digitalocean.com/v2/registry/example/repositories/repo-1/digests?page=1&per_page=1",
                "next": "https://api.digitalocean.com/v2/registry/example/repositories/repo-1/digests?page=3&per_page=1",
                "last": "https://api.digitalocean.com/v2/registry/example/repositories/repo-1/digests?page=3&per_page=1",
            }
        },
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/registry/example/repo-1/digests",
        json=expected,
        status=200,
    )

    get_resp = mock_client.registry.list_repository_manifests(
        registry_name="example", repository_name="repo-1"
    )

    assert get_resp == expected


@responses.activate
def test_container_registry_repository_delete(mock_client: Client, mock_client_url):
    """Test Delete Container Registry Repository Manifest"""

    responses.add(
        responses.DELETE,
        f"{mock_client_url}/v2/registry/example/repo-1/digests/manifest_digest",
        status=204,
    )
    del_resp = mock_client.registry.delete_repository_manifest(
        registry_name="example",
        repository_name="repo-1",
        manifest_digest="manifest_digest",
    )

    assert del_resp is None


@responses.activate
def test_container_registry_start_garbage_collection(
    mock_client: Client, mock_client_url
):
    """Tests Container Registry Start Garbage Collection"""
    expected = None

    responses.add(
        responses.POST,
        f"{mock_client_url}/v2/registry/example/garbage-collection",
        json=expected,
        status=201,
    )

    create_resp = mock_client.registry.run_garbage_collection(registry_name="example")

    assert create_resp == expected


@responses.activate
def test_container_registry_list_garbage_collection(
    mock_client: Client, mock_client_url
):
    """Test List Garbage Collections"""
    expected = {
        "garbage_collections": [
            {
                "uuid": "eff0feee-49c7-4e8f-ba5c-a320c109c8a8",
                "registry_name": "example",
                "status": "requested",
                "created_at": "2020-10-30T21:03:24.000Z",
                "updated_at": "2020-10-30T21:03:44.000Z",
                "blobs_deleted": 42,
                "freed_bytes": 667,
            }
        ],
        "meta": {"total": 1},
    }
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/registry/example/garbage-collections",
        json=expected,
        status=200,
    )

    get_resp = mock_client.registry.list_garbage_collections(registry_name="example")

    assert get_resp == expected


@responses.activate
def test_container_registry_update_garbage_collection(
    mock_client: Client, mock_client_url
):
    """Test Container Registry Update Subscription"""
    expected = {
        "garbage_collection": {
            "uuid": "eff0feee-49c7-4e8f-ba5c-a320c109c8a8",
            "registry_name": "example",
            "status": "requested",
            "created_at": "2020-10-30T21:03:24Z",
            "updated_at": "2020-10-30T21:03:44Z",
            "blobs_deleted": 42,
            "freed_bytes": 667,
        }
    }

    responses.add(
        responses.PUT,
        f"{mock_client_url}/v2/registry/example/garbage-collection/eff0feee-49c7-4e8f-ba5c-a320c109c8a8",
        json=expected,
        status=200,
    )

    update_resp = mock_client.registry.update_garbage_collection(
        registry_name="example",
        garbage_collection_uuid="eff0feee-49c7-4e8f-ba5c-a320c109c8a8",
        body={"cancel": True},
    )

    assert update_resp == expected


@responses.activate
def test_container_registry_options(mock_client: Client, mock_client_url):
    """Test Container Registry's list registry options"""
    expected = {
        "options": {
            "available_regions": ["nyc3", "sfo3", "ams3", "sgp1", "fra1"],
            "subscription_tiers": [
                {
                    "name": "Starter",
                    "slug": "starter",
                    "included_repositories": 1,
                    "included_storage_bytes": 524288000,
                    "allow_storage_overage": False,
                    "included_bandwidth_bytes": 524288000,
                    "monthly_price_in_cents": 0,
                    "eligible": False,
                    "eligibility_reasons": ["OverRepositoryLimit"],
                },
                {
                    "name": "Basic",
                    "slug": "basic",
                    "included_repositories": 5,
                    "included_storage_bytes": 5368709120,
                    "allow_storage_overage": True,
                    "included_bandwidth_bytes": 5368709120,
                    "monthly_price_in_cents": 500,
                    "eligible": True,
                },
                {
                    "name": "Professional",
                    "slug": "professional",
                    "included_repositories": 0,
                    "included_storage_bytes": 107374182400,
                    "allow_storage_overage": True,
                    "included_bandwidth_bytes": 107374182400,
                    "monthly_price_in_cents": 2000,
                    "eligible": True,
                },
            ],
        }
    }

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/registry/options",
        json=expected,
        status=200,
    )

    get_resp = mock_client.registry.get_options()

    assert get_resp == expected
