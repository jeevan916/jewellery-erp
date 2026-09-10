from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.accounting.models import Account, AccountGroup, FinancialPeriod, Voucher, VoucherType
from apps.accounting.services.posting import PostingError, post_voucher


class PostingTests(TestCase):
    def setUp(self):
        assets = AccountGroup.objects.create(code="1000", name="Assets", nature=AccountGroup.Nature.ASSET)
        income = AccountGroup.objects.create(code="4000", name="Income", nature=AccountGroup.Nature.INCOME)
        self.cash = Account.objects.create(code="1001", name="Cash", group=assets)
        self.sales = Account.objects.create(code="4001", name="Sales", group=income)
        self.period = FinancialPeriod.objects.create(name="2026-27", starts_on=date(2026, 4, 1), ends_on=date(2027, 3, 31))
        self.vtype = VoucherType.objects.create(code="JV", name="Journal", category="JOURNAL")

    def voucher(self, number="1"):
        return Voucher.objects.create(voucher_type=self.vtype, number=number, voucher_date=date(2026, 9, 10))

    def balanced_lines(self):
        return [
            {"account_id": self.cash.id, "debit": "100.00"},
            {"account_id": self.sales.id, "credit": "100.00"},
        ]

    def test_balanced_entry_posts(self):
        voucher = self.voucher()
        entry = post_voucher(voucher_id=voucher.id, period_id=self.period.id, lines=self.balanced_lines())
        voucher.refresh_from_db()
        self.assertEqual(entry.total_debit, Decimal("100.0000"))
        self.assertEqual(entry.total_credit, Decimal("100.0000"))
        self.assertEqual(voucher.status, Voucher.Status.POSTED)
        self.assertEqual(entry.lines.count(), 2)

    def test_unbalanced_entry_is_rejected(self):
        voucher = self.voucher()
        with self.assertRaises(PostingError):
            post_voucher(voucher_id=voucher.id, period_id=self.period.id, lines=[
                {"account_id": self.cash.id, "debit": "100"},
                {"account_id": self.sales.id, "credit": "90"},
            ])
        self.assertEqual(voucher.status, Voucher.Status.DRAFT)
        self.assertEqual(voucher.__class__.objects.get(pk=voucher.pk).status, Voucher.Status.DRAFT)

    def test_closed_period_is_rejected(self):
        self.period.status = FinancialPeriod.Status.CLOSED
        self.period.save(update_fields=["status"])
        with self.assertRaises(PostingError):
            post_voucher(voucher_id=self.voucher().id, period_id=self.period.id, lines=self.balanced_lines())

    def test_same_line_debit_and_credit_is_rejected(self):
        voucher = self.voucher()
        with self.assertRaises(PostingError):
            post_voucher(voucher_id=voucher.id, period_id=self.period.id, lines=[
                {"account_id": self.cash.id, "debit": "100", "credit": "100"},
                {"account_id": self.sales.id, "credit": "100"},
            ])
