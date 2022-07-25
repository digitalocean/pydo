""" test_billing.py
    Integration Test for Billing
"""
import os
import pytest
from digitalocean import Client


pytestmark = pytest.mark.real_billing


def test_billing_get_balance(integration_client: Client):
    """Testing billing's GET customer balance of billing."""

    get_resp = integration_client.balance.get()

    assert get_resp["account_balance"] == "0.00"


def test_billing_list_history(integration_client: Client):
    """Testing listing billing history."""

    get_resp = integration_client.billing_history.list()

    assert (
        get_resp["billing_history"][0]["type"] == "Invoice"
        or get_resp["billing_history"][0]["type"] == "Payment"
    )


def test_billing_list_invoices(integration_client: Client):
    """Testing listing invoice."""

    get_resp = integration_client.billing_history.list()

    assert (
        get_resp["billing_history"][0]["type"] == "Invoice"
        or get_resp["billing_history"][0]["type"] == "Payment"
    )


def test_billing_get_invoice_by_uuid(integration_client: Client, invoice_uuid_param):
    """Testing GETting invoice by uuid."""

    get_resp = integration_client.invoices.get_by_uuid(invoice_uuid=invoice_uuid_param)

    assert get_resp["billing_history"]["type"] == "Invoice"


def test_billing_get_invoice_csv_by_uuid(
    integration_client: Client, invoice_uuid_param
):
    """Testing GETting invoice csv by invoice uuid."""

    get_resp = integration_client.invoices.get_csv_by_uuid(
        invoice_uuid=invoice_uuid_param
    )

    assert "product,group_description," in get_resp


def test_billing_get_invoice_pdf_by_uuid(
    integration_client: Client, invoice_uuid_param
):
    """Testing GETting invoice pdf by invoice uuid."""

    get_resp = integration_client.invoices.get_pdf_by_uuid(
        invoice_uuid=invoice_uuid_param
    )

    pdf_bytes = list(get_resp)[0]

    file = open("tests/integration/invoice.pdf", "a")
    file.write(str(pdf_bytes))
    file.close()

    assert os.path.getsize("tests/integration/invoice.pdf") > 0
    os.remove("tests/integration/invoice.pdf")


def test_billing_get_invoice_summary_by_uuid(
    integration_client: Client, invoice_uuid_param
):
    """Testing GETting invoice summary by uuid."""

    get_resp = integration_client.invoices.get_summary_by_uuid(
        invoice_uuid=invoice_uuid_param
    )

    assert get_resp["user_company"] == "DigitalOcean"
