from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounting.models import Account, AccountGroup, FinancialPeriod, Voucher, VoucherType
from apps.accounting.services.posting import PostingError, post_voucher


class PostingTests(TestCase):
    def setUp(self):
        group = AccountGroup.objects.create(code="1000", name="Assets", nature=AccountGroup.Nature.ASSET)
        self.cash = Account.objects.create(code="1001", name="Cash", group=group)
        self.sales = Account.objects.create(code="4001", name="Sales", group=AccountGroup.objects.create(code="4000", name="Income", nature=AccountGroup.Nature.INCOME))
        self.period = FinancialPeriod.objects.create(name="2026-27", starts_on=date(2026, 4, 1), ends_on=date(2027, 3, 31))
        self.vtype = VoucherType.objects.create(code="JV", name="Journal", category="JOURNAL")

    def make_voucher(self):
        return Voucher.objects.create(voucher_type=self.vtype, number="1", voucher_date=date(2026, 9, 10))

    def test_balanced_entry_posts(self):
        voucher = self.make_voucher()
        entry = post_voucher(voucher_id=voucher.id, period_id=self.period.id, lines=[
            {"account_id": self.cash.id, "debit": "100.00"},
            {"account_id": self.sales.id, "credit": "100.00"},
        ])
        self.assertEqual(entry.total_debit, Decimal("100.0000"))
        self.assertEqual(entry.total_credit, Decimal("100.0000"))
        self.assertEqual(voucher.refresh_from_db() or voucher.status, Voucher.Status.POSTED)

    def test_unbalanced_entry_rejected_atomically(self):
        voucher = self.make_voucher()
        with self.assertRaises(PostingError):
            post_voucher(voucher_id=voucher.id, period_id=self.period.id, lines=[
                {"account_id": self.cash.id, "debit": "100.00"},
                {"account_id": self.sales.id, "credit": "90.00"},
            ])
        self.assertFalse(hasattr(voucher, "journal_entry"))
        self.assertEqual(voucher.status, Voucher.Status.DRAFT)

    def test_closed_period_rejected(self):
        self.period.status = FinancialPeriod.Status.CLOSED
        self.period.save(update_fields=["status"])
        with self.assertRaises(PostingError):
            post_voucher(voucher_id=self.make_voucher().id, period_id=self.period.id, lines=[
                {"account_id": self.cash.id, "debit": "100.00"},
                {"account_id": self.sales.id, "credit": "100.00"},
            ])
