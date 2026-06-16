# pylint: disable=line-too-long
"""Mock tests for droplet actions helpers."""
from unittest.mock import Mock
import pytest

from azure.core.exceptions import HttpResponseError
from pydo.helpers.droplet_actions import (
    perform_action,
    power_on,
    power_off,
    reboot,
    shutdown,
    power_cycle,
    snapshot,
    resize,
    rename,
    rebuild,
    password_reset,
)


class FakeDropletActions:
    """Fake DropletActions operations for testing."""

    def __init__(self):
        self.post = Mock()


class FakeClient:
    """Fake client for testing."""

    def __init__(self):
        self.droplet_actions = FakeDropletActions()


@pytest.fixture
def fake_client():
    """Returns a fake client for testing."""
    return FakeClient()


def test_perform_action_success(fake_client):
    """Test perform_action with successful response."""
    fake_client.droplet_actions.post.return_value = {
        "action": {
            "id": 123,
            "status": "in-progress",
            "type": "power_on",
            "started_at": "2020-02-20T00:00:00Z",
            "completed_at": None,
            "resource_id": 456,
            "resource_type": "droplet",
            "region": {"slug": "nyc3"},
        }
    }

    result = perform_action(fake_client, 456, "power_on")

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "power_on"}
    )
    assert result["id"] == 123
    assert result["status"] == "in-progress"
    assert result["type"] == "power_on"


def test_perform_action_with_extra_params(fake_client):
    """Test perform_action with additional parameters."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 789, "status": "in-progress", "type": "resize"}
    }

    result = perform_action(fake_client, 456, "resize", size="s-2vcpu-4gb", disk=True)

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "resize", "size": "s-2vcpu-4gb", "disk": True}
    )
    assert result["id"] == 789


def test_perform_action_without_action_key(fake_client):
    """Test perform_action when response doesn't have 'action' key."""
    fake_client.droplet_actions.post.return_value = {
        "id": 123,
        "status": "in-progress",
    }

    result = perform_action(fake_client, 456, "power_on")

    assert result["id"] == 123
    assert result["status"] == "in-progress"


def test_perform_action_http_error(fake_client):
    """Test perform_action wraps HttpResponseError."""
    mock_response = Mock()
    mock_response.status_code = 404
    error = HttpResponseError(message="Droplet not found", response=mock_response)
    fake_client.droplet_actions.post.side_effect = error

    with pytest.raises(HttpResponseError) as exc_info:
        perform_action(fake_client, 456, "power_on")

    assert "Failed to perform 'power_on' action on droplet 456" in str(exc_info.value)


def test_perform_action_unexpected_error(fake_client):
    """Test perform_action wraps unexpected exceptions."""
    fake_client.droplet_actions.post.side_effect = ValueError("Unexpected error")

    with pytest.raises(HttpResponseError) as exc_info:
        perform_action(fake_client, 456, "power_on")

    assert "Unexpected error performing 'power_on' action on droplet 456" in str(
        exc_info.value
    )


def test_power_on(fake_client):
    """Test power_on helper."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 1, "type": "power_on", "status": "in-progress"}
    }

    result = power_on(fake_client, 456)

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "power_on"}
    )
    assert result["type"] == "power_on"


def test_power_off(fake_client):
    """Test power_off helper."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 2, "type": "power_off", "status": "in-progress"}
    }

    result = power_off(fake_client, 456)

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "power_off"}
    )
    assert result["type"] == "power_off"


def test_reboot(fake_client):
    """Test reboot helper."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 3, "type": "reboot", "status": "in-progress"}
    }

    result = reboot(fake_client, 456)

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "reboot"}
    )
    assert result["type"] == "reboot"


def test_shutdown(fake_client):
    """Test shutdown helper."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 4, "type": "shutdown", "status": "in-progress"}
    }

    result = shutdown(fake_client, 456)

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "shutdown"}
    )
    assert result["type"] == "shutdown"


def test_power_cycle(fake_client):
    """Test power_cycle helper."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 5, "type": "power_cycle", "status": "in-progress"}
    }

    result = power_cycle(fake_client, 456)

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "power_cycle"}
    )
    assert result["type"] == "power_cycle"


def test_snapshot_without_name(fake_client):
    """Test snapshot helper without name."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 6, "type": "snapshot", "status": "in-progress"}
    }

    result = snapshot(fake_client, 456)

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "snapshot"}
    )
    assert result["type"] == "snapshot"


def test_snapshot_with_name(fake_client):
    """Test snapshot helper with name."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 7, "type": "snapshot", "status": "in-progress"}
    }

    result = snapshot(fake_client, 456, name="my-snapshot")

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "snapshot", "name": "my-snapshot"}
    )
    assert result["type"] == "snapshot"


def test_resize_without_disk(fake_client):
    """Test resize helper without disk resize."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 8, "type": "resize", "status": "in-progress"}
    }

    result = resize(fake_client, 456, size="s-2vcpu-4gb")

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "resize", "size": "s-2vcpu-4gb", "disk": False}
    )
    assert result["type"] == "resize"


def test_resize_with_disk(fake_client):
    """Test resize helper with disk resize."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 9, "type": "resize", "status": "in-progress"}
    }

    result = resize(fake_client, 456, size="s-2vcpu-4gb", disk=True)

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "resize", "size": "s-2vcpu-4gb", "disk": True}
    )
    assert result["type"] == "resize"


def test_rename(fake_client):
    """Test rename helper."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 10, "type": "rename", "status": "in-progress"}
    }

    result = rename(fake_client, 456, name="new-droplet-name")

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "rename", "name": "new-droplet-name"}
    )
    assert result["type"] == "rename"


def test_rebuild_with_slug(fake_client):
    """Test rebuild helper with image slug."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 11, "type": "rebuild", "status": "in-progress"}
    }

    result = rebuild(fake_client, 456, image="ubuntu-20-04-x64")

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "rebuild", "image": "ubuntu-20-04-x64"}
    )
    assert result["type"] == "rebuild"


def test_rebuild_with_image_id(fake_client):
    """Test rebuild helper with image ID."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 12, "type": "rebuild", "status": "in-progress"}
    }

    result = rebuild(fake_client, 456, image=123456789)

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "rebuild", "image": 123456789}
    )
    assert result["type"] == "rebuild"


def test_password_reset(fake_client):
    """Test password_reset helper."""
    fake_client.droplet_actions.post.return_value = {
        "action": {"id": 13, "type": "password_reset", "status": "in-progress"}
    }

    result = password_reset(fake_client, 456)

    fake_client.droplet_actions.post.assert_called_once_with(
        droplet_id=456, body={"type": "password_reset"}
    )
    assert result["type"] == "password_reset"


def test_all_helpers_handle_errors(fake_client):
    """Test that all helpers properly propagate errors."""
    mock_response = Mock()
    mock_response.status_code = 500
    error = HttpResponseError(message="Internal Server Error", response=mock_response)
    fake_client.droplet_actions.post.side_effect = error

    helpers_to_test = [
        (power_on, (fake_client, 456)),
        (power_off, (fake_client, 456)),
        (reboot, (fake_client, 456)),
        (shutdown, (fake_client, 456)),
        (power_cycle, (fake_client, 456)),
        (snapshot, (fake_client, 456)),
        (resize, (fake_client, 456, "s-1vcpu-2gb")),
        (rename, (fake_client, 456, "new-name")),
        (rebuild, (fake_client, 456, "ubuntu-20-04-x64")),
        (password_reset, (fake_client, 456)),
    ]

    for helper_func, args in helpers_to_test:
        with pytest.raises(HttpResponseError):
            helper_func(*args)
