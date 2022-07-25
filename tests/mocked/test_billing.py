"""Mock tests for the billing API resource."""
import io
import PyPDF2
import responses

from digitalocean import Client


@responses.activate
def test_get_customer_balance(mock_client: Client, mock_client_url):
    """Mocks billing's GET customer balance operation."""
    expected = {
        "month_to_date_balance": "0.00",
        "account_balance": "0.00",
        "month_to_date_usage": "0.00",
        "generated_at": "2019-07-09T15:01:12Z",
    }
    responses.add(
        responses.GET, f"{mock_client_url}/v2/customers/my/balance", json=expected
    )
    balance = mock_client.balance.get()

    assert balance == expected


@responses.activate
def test_list_billing_history(mock_client: Client, mock_client_url):
    """Mocks billing's GET billing history operation."""
    expected = {
        "billing_history": [
            {
                "description": "Invoice for May 2018",
                "amount": "12.34",
                "invoice_id": "123",
                "invoice_uuid": "example-uuid",
                "date": "2018-06-01T08:44:38Z",
                "type": "Invoice",
            },
            {
                "description": "Payment (MC 2018)",
                "amount": "-12.34",
                "date": "2018-06-02T08:44:38Z",
                "type": "Payment",
            },
        ],
        "links": {"pages": {}},
        "meta": {"total": 5},
    }
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/customers/my/billing_history",
        json=expected,
    )
    balance = mock_client.billing_history.list()

    assert balance == expected


@responses.activate
def test_list_invoices(mock_client: Client, mock_client_url):
    """Mocks billing's GET a list of invoices."""
    expected = {
        "invoices": [
            {
                "invoice_uuid": "22737513-0ea7-4206-8ceb-98a575af7681",
                "amount": "12.34",
                "invoice_period": "2019-12",
            },
            {
                "invoice_uuid": "fdabb512-6faf-443c-ba2e-665452332a9e",
                "amount": "23.45",
                "invoice_period": "2019-11",
            },
        ],
        "invoice_preview": {
            "invoice_uuid": "1afe95e6-0958-4eb0-8d9a-9c5060d3ef03",
            "amount": "34.56",
            "invoice_period": "2020-02",
            "updated_at": "2020-02-23T06:31:50Z",
        },
        "links": {"pages": {}},
        "meta": {"total": 70},
    }
    responses.add(
        responses.GET, f"{mock_client_url}/v2/customers/my/invoices", json=expected
    )
    balance = mock_client.invoices.list()

    assert balance == expected


@responses.activate
def test_get_invoice_by_uuid(mock_client: Client, mock_client_url):
    """Mocks billing's GET invoice by uuid."""
    expected = {
        "invoice_items": [
            {
                "product": "Kubernetes Clusters",
                "resource_uuid": "711157cb-37c8-4817-b371-44fa3504a39c",
                "group_description": "my-doks-cluster",
                "description": "a56e086a317d8410c8b4cfd1f4dc9f82",
                "amount": "12.34",
                "duration": "744",
                "duration_unit": "Hours",
                "start_time": "2020-01-01T00:00:00Z",
                "end_time": "2020-02-01T00:00:00Z",
            },
            {
                "product": "Spaces Subscription",
                "description": "Spaces ($5/mo 250GB storage & 1TB bandwidth)",
                "amount": "34.45",
                "duration": "744",
                "duration_unit": "Hours",
                "start_time": "2020-01-01T00:00:00Z",
                "end_time": "2020-02-01T00:00:00Z",
            },
        ],
        "links": {"pages": {}},
        "meta": {"total": 6},
    }

    responses.add(
        responses.GET, f"{mock_client_url}/v2/customers/my/invoices/1", json=expected
    )
    balance = mock_client.invoices.get_by_uuid(invoice_uuid=1)

    assert balance == expected


@responses.activate
def test_get_invoice_csv_by_uuid(mock_client: Client, mock_client_url):
    """Mocks billing's GET invoice CSV by uuid."""
    expected = "product,group_description,description,hours,\
        start,end,USD,project_name,category\
        Floating IPs,,Unused Floating IP - 1.1.1.1,100,2020-07-01 00:00:00\
             +0000,2020-07-22 18:14:39 +0000,$3.11,,iaas\
            Taxes,,STATE SALES TAX (6.25%),,2020-07-01 00:00:00\
                 +0000,2020-07-31 23:59:59 +0000,$0.16,,iaas"

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/customers/my/invoices/1/csv",
        json=expected,
    )
    balance = mock_client.invoices.get_csv_by_uuid(invoice_uuid=1)

    assert balance == expected


@responses.activate
def test_get_invoice_pdf_by_uuid(mock_client: Client, mock_client_url):
    """Mocks billing's GET invoice PDF by uuid."""
    expected = "product,group_description,description,hours\
,start,end,USD,project_name,category\
Floating IPs,,Unused Floating IP - 1.1.1.1,100,2020-07-01\
00:00:00 +0000,2020-07-22 18:14:39 +0000,$3.11,,iaas\
Taxes,,STATE SALES TAX (6.25%),,2020-07-01 00:00:00 \
+0000,2020-07-31 23:59:59 +0000,$0.16,,iaas"

    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/customers/my/invoices/1/pdf",
        json=expected,
    )
    invoices = mock_client.invoices.get_pdf_by_uuid(invoice_uuid=1)
    list_in = list(invoices)

    assert "group_description" in str(list_in)


@responses.activate
def test_get_invoice_summary_by_uuid(mock_client: Client, mock_client_url):
    """Mocks billing's GET invoice summary by uuid."""
    expected = {
        "invoice_uuid": "1",
        "billing_period": "2020-01",
        "amount": "27.13",
        "user_name": "Sammy Shark",
        "user_billing_address": {
            "address_line1": "101 Shark Row",
            "city": "Atlantis",
            "region": "OC",
            "postal_code": "12345",
            "country_iso2_code": "US",
            "created_at": "2019-09-03T16:34:46.000+00:00",
            "updated_at": "2019-09-03T16:34:46.000+00:00",
        },
        "user_company": "DigitalOcean",
        "user_email": "sammy@digitalocean.com",
        "product_charges": {
            "name": "Product usage charges",
            "amount": "12.34",
            "items": [
                {"amount": "10.00", "name": "Spaces Subscription", "count": "1"},
                {"amount": "2.34", "name": "Database Clusters", "count": "1"},
            ],
        },
        "overages": {"name": "Overages", "amount": "3.45"},
        "taxes": {"name": "Taxes", "amount": "4.56"},
        "credits_and_adjustments": {"name": "Credits & adjustments", "amount": "6.78"},
    }
    responses.add(
        responses.GET,
        f"{mock_client_url}/v2/customers/my/invoices/1/summary",
        json=expected,
    )
    invoice = mock_client.invoices.get_summary_by_uuid(invoice_uuid="1")

    assert invoice == expected
