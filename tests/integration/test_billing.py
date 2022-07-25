""" test_billing.py
    Integration Test for Billing
"""

import PyPDF2
from digitalocean import Client
from tests.integration import defaults


def test_billing_get_balance(integration_client: Client):
    """Testing billing's GET customer balance of billing."""

    get_resp = integration_client.balance.get()

    assert get_resp["month_to_date_balance"] == "0.00"


def test_billing_list_history(integration_client: Client):
    """Testing listing billing history."""

    get_resp = integration_client.billing_history.list()

    assert get_resp["month_to_date_balance"] == "0.00"


def test_billing_list_invoices(integration_client: Client):
    """Testing listing invoice."""

    get_resp = integration_client.billing_history.list()

    assert get_resp["billing_history"]["type"] == "Invoice"


def test_billing_get_invoice_by_uuid(integration_client: Client):
    """Testing GETting invoice by uuid."""

    get_resp = integration_client.invoices.get_by_uuid(
        invoice_uuid=defaults.INVOICE_UUID_PARM
    )

    assert get_resp["billing_history"]["type"] == "Invoice"


def test_billing_get_invoice_csv_by_uuid(integration_client: Client):
    """Testing GETting invoice csv by invoice uuid."""

    get_resp = integration_client.invoices.get_csv_by_uuid(
        invoice_uuid=defaults.INVOICE_UUID_PARM
    )

    assert "product,group_description," in get_resp


# not sure how to test if a pdf is passed
def test_billing_get_invoice_pdf_by_uuid(integration_client: Client):
    """Testing GETting invoice pdf by invoice uuid."""

    get_resp = integration_client.invoices.get_pdf_by_uuid(
        invoice_uuid=defaults.INVOICE_UUID_PARM
    )

    list_in = list(get_resp)

    assert "product" in str(list_in)


def test_billing_get_invoice_summary_by_uuid(integration_client: Client):
    """Testing GETting invoice summary by uuid."""

    get_resp = integration_client.invoices.get_pdf_by_uuid(
        invoice_uuid=defaults.INVOICE_UUID_PARM
    )

    assert get_resp["user_company"] == "DigitalOcean"
