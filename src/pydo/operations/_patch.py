# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
"""Customize generated code here.

Follow our quickstart for examples: https://aka.ms/azsdk/python/dpcodegen/python/customize
"""
from typing import TYPE_CHECKING

from ._operations import DropletsOperations as Droplets
from ._operations import KubernetesOperations as Kubernetes
from ._operations import InvoicesOperations as Invoices

if TYPE_CHECKING:
    # pylint: disable=unused-import,ungrouped-imports
    pass


__all__ = []


def patch_sdk():
    """Do not remove from this file.

    `patch_sdk` is a last resort escape hatch that allows you to do customizations
    you can't accomplish using the techniques described in
    https://aka.ms/azsdk/python/dpcodegen/python/customize
    """

    # Fix kubernetes.get_kubeconfig to return raw YAML content instead of trying to parse as JSON
    def _get_kubeconfig(self, cluster_id, **kwargs):
        """Get a Kubernetes config file for the specified cluster."""
        # Call the original method but with raw response
        response = self._client.get(
            f"/v2/kubernetes/clusters/{cluster_id}/kubeconfig",
            **kwargs
        )
        return response.content

    Kubernetes.get_kubeconfig = _get_kubeconfig

    # Fix invoices.get_pdf_by_uuid to return raw PDF content instead of trying to parse as JSON
    def _get_pdf_by_uuid(self, invoice_uuid, **kwargs):
        """Get a PDF invoice by UUID."""
        # Call the original method but with raw response
        response = self._client.get(
            f"/v2/customers/my/invoices/{invoice_uuid}/pdf",
            **kwargs
        )
        return response.content

    Invoices.get_pdf_by_uuid = _get_pdf_by_uuid
