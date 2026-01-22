"""This file is for patching generated code.""" 
import functools
from typing import Any, Callable

from ._operations import RegistryOperations


def patch_registry_delete_repository_manifest(
    func: Callable[..., Any]
) -> Callable[..., Any]:
    """This patch is to address a bug in the DO API.

    The delete_repository_manifest endpoint does not support url encoding.
    This patch will skip url encoding for the manifest_digest parameter.
    """

    @functools.wraps(func)
    def wrapper(
        self, manifest_digest: str, *args: Any, **kwargs: Any
    ) -> Callable[..., Any]:
        return func(self, manifest_digest, *args, **kwargs, _skip_url_encoding=True)

    return wrapper


RegistryOperations.delete_repository_manifest = patch_registry_delete_repository_manifest(
    RegistryOperations.delete_repository_manifest
)