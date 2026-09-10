from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.accounting.models import Account, AccountGroup, Party, VoucherType
from apps.accounting.services.sales import create_sales_invoice, post_sales_invoice


class SalesPostingTests(TestCase):
    def setUp(self):
        assets = AccountGroup.objects.create(code="1000", name="Assets", nature=AccountGroup.Nature.ASSET)
        income = AccountGroup.objects.create(code="4000", name="Income", nature=AccountGroup.Nature.INCOME)
        liability = AccountGroup.objects.create(code="2000", name="Liabilities", nature=AccountGroup.Nature.LIABILITY)
        self.customer_account = Account.objects.create(code="1100", name="Customer Control", group=assets, is_party_account=True)
        self.sales_account = Account.objects.create(code="4001", name="Jewellery Sales", group=income)
        self.cgst_account = Account.objects.create(code="2101", name="Output CGST", group=liability)
        self.sgst_account = Account.objects.create(code="2102", name="Output SGST", group=liability)
        self.customer = Party.objects.create(
            code="C001", name="Test Customer", party_type=Party.PartyType.CUSTOMER,
            account=self.customer_account,
        )
        from apps.accounting.models import FinancialPeriod
        self.period = FinancialPeriod.objects.create(
            name="2026-27", starts_on=date(2026, 4, 1), ends_on=date(2027, 3, 31)
        )
        VoucherType.objects.create(code="SALES", name="Sales", category="SALES", prefix="INV")

    def test_create_and_post_sales_invoice(self):
        invoice = create_sales_invoice(
            customer_id=self.customer.id,
            voucher_number="INV-1",
            invoice_number="INV-1",
            invoice_date=date(2026, 9, 10),
            lines=[{"description": "Gold Ring", "quantity": "1", "rate": "100000", "discount": "0"}],
            cgst="1500", sgst="1500",
        )
        self.assertEqual(invoice.status, invoice.Status.DRAFT)
        posted, bill, entry = post_sales_invoice(
            invoice_id=invoice.id,
            financial_period_id=self.period.id,
            receivable_account_id=self.customer_account.id,
            sales_account_id=self.sales_account.id,
            cgst_account_id=self.cgst_account.id,
            sgst_account_id=self.sgst_account.id,
        )
        self.assertEqual(posted.status, posted.Status.POSTED)
        self.assertEqual(bill.amount, Decimal("103000.0000"))
        self.assertEqual(entry.total_debit, Decimal("103000.0000"))
        self.assertEqual(entry.total_credit, Decimal("103000.0000"))
        self.assertEqual(entry.lines.count(), 4)

    def test_cgst_requires_account(self):
        invoice = create_sales_invoice(
            customer_id=self.customer.id, voucher_number="INV-2", invoice_number="INV-2",
            invoice_date=date(2026, 9, 10),
            lines=[{"description": "Chain", "quantity": "1", "rate": "1000"}], cgst="90",
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            post_sales_invoice(
                invoice_id=invoice.id, financial_period_id=self.period.id,
                receivable_account_id=self.customer_account.id, sales_account_id=self.sales_account.id,
            )
