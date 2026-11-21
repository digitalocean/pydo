"""Helper functions for Droplet Actions."""

from typing import Any, Dict, Optional

from azure.core.exceptions import HttpResponseError


def perform_action(
    client, droplet_id: int, action_type: str, **extra: Any
) -> Dict[str, Any]:
    """
    Perform a generic action on a droplet.

    Args:
        client: The pydo Client instance.
        droplet_id: The ID of the droplet.
        action_type: The type of action to perform.
        **extra: Additional parameters for specific actions.

    Returns:
        Dict containing the action response, normalized to return the
        'action' dict if present.

    Raises:
        HttpResponseError: If the API request fails.

    Example:
        >>> from pydo import Client
        >>> client = Client(token="your_token")
        >>> action = perform_action(client, 123456, "power_on")
        >>> print(action['status'])
    """
    try:
        body = {"type": action_type}
        body.update(extra)

        response = client.droplet_actions.post(droplet_id=droplet_id, body=body)

        # Normalize response: return action dict if present
        if isinstance(response, dict) and "action" in response:
            return response["action"]
        return response
    except HttpResponseError as e:
        # Re-raise with additional context
        msg = (
            f"Failed to perform '{action_type}' action on droplet "
            f"{droplet_id}: {e.message}"
        )
        raise HttpResponseError(msg, response=e.response) from e
    except Exception as e:
        # Wrap unexpected exceptions
        msg = (
            f"Unexpected error performing '{action_type}' action on "
            f"droplet {droplet_id}: {str(e)}"
        )
        raise HttpResponseError(msg) from e


def power_on(client, droplet_id: int) -> Dict[str, Any]:
    """
    Power on a droplet.

    Args:
        client: The pydo Client instance.
        droplet_id: The ID of the droplet.

    Returns:
        Dict containing the action response.

    Raises:
        HttpResponseError: If the API request fails.

    Example:
        >>> from pydo import Client
        >>> client = Client(token="your_token")
        >>> action = power_on(client, 123456)
    """
    return perform_action(client, droplet_id, "power_on")


def power_off(client, droplet_id: int) -> Dict[str, Any]:
    """
    Power off a droplet (hard shutdown).

    Args:
        client: The pydo Client instance.
        droplet_id: The ID of the droplet.

    Returns:
        Dict containing the action response.

    Raises:
        HttpResponseError: If the API request fails.

    Example:
        >>> from pydo import Client
        >>> client = Client(token="your_token")
        >>> action = power_off(client, 123456)
    """
    return perform_action(client, droplet_id, "power_off")


def reboot(client, droplet_id: int) -> Dict[str, Any]:
    """
    Reboot a droplet gracefully.

    Args:
        client: The pydo Client instance.
        droplet_id: The ID of the droplet.

    Returns:
        Dict containing the action response.

    Raises:
        HttpResponseError: If the API request fails.

    Example:
        >>> from pydo import Client
        >>> client = Client(token="your_token")
        >>> action = reboot(client, 123456)
    """
    return perform_action(client, droplet_id, "reboot")


def shutdown(client, droplet_id: int) -> Dict[str, Any]:
    """
    Shutdown a droplet gracefully.

    Args:
        client: The pydo Client instance.
        droplet_id: The ID of the droplet.

    Returns:
        Dict containing the action response.

    Raises:
        HttpResponseError: If the API request fails.

    Example:
        >>> from pydo import Client
        >>> client = Client(token="your_token")
        >>> action = shutdown(client, 123456)
    """
    return perform_action(client, droplet_id, "shutdown")


def power_cycle(client, droplet_id: int) -> Dict[str, Any]:
    """
    Power cycle a droplet (similar to pressing reset button).

    Args:
        client: The pydo Client instance.
        droplet_id: The ID of the droplet.

    Returns:
        Dict containing the action response.

    Raises:
        HttpResponseError: If the API request fails.

    Example:
        >>> from pydo import Client
        >>> client = Client(token="your_token")
        >>> action = power_cycle(client, 123456)
    """
    return perform_action(client, droplet_id, "power_cycle")


def snapshot(client, droplet_id: int, name: Optional[str] = None) -> Dict[str, Any]:
    """
    Take a snapshot of a droplet.

    Args:
        client: The pydo Client instance.
        droplet_id: The ID of the droplet.
        name: Optional name for the snapshot.

    Returns:
        Dict containing the action response.

    Raises:
        HttpResponseError: If the API request fails.

    Example:
        >>> from pydo import Client
        >>> client = Client(token="your_token")
        >>> action = snapshot(client, 123456, name="my-snapshot")
    """
    kwargs = {}
    if name:
        kwargs["name"] = name
    return perform_action(client, droplet_id, "snapshot", **kwargs)


def resize(client, droplet_id: int, size: str, disk: bool = False) -> Dict[str, Any]:
    """
    Resize a droplet.

    Args:
        client: The pydo Client instance.
        droplet_id: The ID of the droplet.
        size: The slug of the new size (e.g., 's-1vcpu-2gb').
        disk: If True, permanently resize the disk. Default is False.

    Returns:
        Dict containing the action response.

    Raises:
        HttpResponseError: If the API request fails.

    Example:
        >>> from pydo import Client
        >>> client = Client(token="your_token")
        >>> action = resize(client, 123456, size="s-2vcpu-4gb", disk=True)
    """
    return perform_action(client, droplet_id, "resize", size=size, disk=disk)


def rename(client, droplet_id: int, name: str) -> Dict[str, Any]:
    """
    Rename a droplet.

    Args:
        client: The pydo Client instance.
        droplet_id: The ID of the droplet.
        name: The new name for the droplet.

    Returns:
        Dict containing the action response.

    Raises:
        HttpResponseError: If the API request fails.

    Example:
        >>> from pydo import Client
        >>> client = Client(token="your_token")
        >>> action = rename(client, 123456, name="new-droplet-name")
    """
    return perform_action(client, droplet_id, "rename", name=name)


def rebuild(client, droplet_id: int, image: Any) -> Dict[str, Any]:
    """
    Rebuild a droplet from a new base image.

    Args:
        client: The pydo Client instance.
        droplet_id: The ID of the droplet.
        image: The image ID (int) or slug (str) to rebuild from.

    Returns:
        Dict containing the action response.

    Raises:
        HttpResponseError: If the API request fails.

    Example:
        >>> from pydo import Client
        >>> client = Client(token="your_token")
        >>> action = rebuild(client, 123456, image="ubuntu-20-04-x64")
    """
    return perform_action(client, droplet_id, "rebuild", image=image)


def password_reset(client, droplet_id: int) -> Dict[str, Any]:
    """
    Reset the root password for a droplet.

    A new password will be emailed to the account owner.

    Args:
        client: The pydo Client instance.
        droplet_id: The ID of the droplet.

    Returns:
        Dict containing the action response.

    Raises:
        HttpResponseError: If the API request fails.

    Example:
        >>> from pydo import Client
        >>> client = Client(token="your_token")
        >>> action = password_reset(client, 123456)
    """
    return perform_action(client, droplet_id, "password_reset")
