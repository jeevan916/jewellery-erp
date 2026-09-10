from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.accounting.models import (
    Account,
    AccountGroup,
    BillReference,
    FinancialPeriod,
    Party,
    Payment,
    Voucher,
    VoucherType,
)
from apps.accounting.services.billwise import BillWiseError, allocate_payment, deallocate_payment
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


class BillWiseAllocationTests(TestCase):
    def setUp(self):
        assets = AccountGroup.objects.create(code="1000", name="Assets", nature=AccountGroup.Nature.ASSET)
        receivables = AccountGroup.objects.create(code="1100", name="Receivables", nature=AccountGroup.Nature.ASSET)
        self.customer_account = Account.objects.create(
            code="1101", name="Customer A", group=receivables, is_party_account=True
        )
        self.supplier_account = Account.objects.create(
            code="2101", name="Supplier A", group=AccountGroup.objects.create(
                code="2000", name="Liabilities", nature=AccountGroup.Nature.LIABILITY
            ), is_party_account=True
        )
        self.cash = Account.objects.create(code="1001", name="Cash", group=assets, is_cash=True)
        self.vtype = VoucherType.objects.create(code="RCPT", name="Receipt", category="RECEIPT")
        self.party = Party.objects.create(
            code="C001", name="Customer A", party_type=Party.PartyType.CUSTOMER, account=self.customer_account
        )

    def make_payment(self, amount="1000.00", payment_type=Payment.PaymentType.RECEIPT, number="1"):
        voucher = Voucher.objects.create(voucher_type=self.vtype, number=number, voucher_date=date(2026, 9, 10), status=Voucher.Status.POSTED)
        return Payment.objects.create(
            party=self.party,
            voucher=voucher,
            payment_date=date(2026, 9, 10),
            payment_type=payment_type,
            amount=amount,
            status=Payment.Status.POSTED,
        )

    def make_bill(self, amount="1000.00", number="INV-1"):
        voucher = Voucher.objects.create(voucher_type=self.vtype, number=f"B-{number}", voucher_date=date(2026, 9, 10), status=Voucher.Status.POSTED)
        return BillReference.objects.create(
            party=self.party,
            voucher=voucher,
            bill_number=number,
            bill_date=date(2026, 9, 10),
            bill_type=BillReference.BillType.RECEIVABLE,
            amount=amount,
        )

    def test_partial_payment_and_multiple_invoices(self):
        payment = self.make_payment("1000.00")
        bill1 = self.make_bill("600.00", "INV-1")
        bill2 = self.make_bill("800.00", "INV-2")

        allocate_payment(payment_id=payment.id, bill_id=bill1.id, amount="400.00")
        allocate_payment(payment_id=payment.id, bill_id=bill2.id, amount="600.00")

        bill1.refresh_from_db()
        bill2.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(bill1.outstanding_amount, Decimal("200.0000"))
        self.assertEqual(bill2.outstanding_amount, Decimal("200.0000"))
        self.assertEqual(payment.unallocated_amount, Decimal("0.0000"))

    def test_over_allocation_is_rejected(self):
        payment = self.make_payment("500.00")
        bill = self.make_bill("400.00")
        with self.assertRaises(BillWiseError):
            allocate_payment(payment_id=payment.id, bill_id=bill.id, amount="500.00")
        self.assertEqual(bill.allocations.count(), 0)

    def test_overpayment_remains_unallocated_advance(self):
        payment = self.make_payment("1000.00")
        bill = self.make_bill("600.00")
        allocate_payment(payment_id=payment.id, bill_id=bill.id, amount="600.00")
        payment.refresh_from_db()
        self.assertEqual(payment.unallocated_amount, Decimal("400.0000"))
        self.assertEqual(bill.outstanding_amount, Decimal("0.0000"))

    def test_wrong_party_cannot_be_allocated(self):
        other_account = Account.objects.create(
            code="1102", name="Customer B", group=self.customer_account.group, is_party_account=True
        )
        other_party = Party.objects.create(
            code="C002", name="Customer B", party_type=Party.PartyType.CUSTOMER, account=other_account
        )
        payment = self.make_payment()
        voucher = Voucher.objects.create(voucher_type=self.vtype, number="B-OTHER", voucher_date=date(2026, 9, 10), status=Voucher.Status.POSTED)
        bill = BillReference.objects.create(
            party=other_party, voucher=voucher, bill_number="INV-X", bill_date=date(2026, 9, 10),
            bill_type=BillReference.BillType.RECEIVABLE, amount="100.00"
        )
        with self.assertRaises(BillWiseError):
            allocate_payment(payment_id=payment.id, bill_id=bill.id, amount="100.00")

    def test_deallocation_reopens_settled_bill(self):
        payment = self.make_payment("500.00")
        bill = self.make_bill("500.00")
        allocation = allocate_payment(payment_id=payment.id, bill_id=bill.id, amount="500.00")
        bill.refresh_from_db()
        self.assertEqual(bill.status, BillReference.Status.SETTLED)
        deallocate_payment(allocation_id=allocation.id)
        bill.refresh_from_db()
        self.assertEqual(bill.status, BillReference.Status.OPEN)
        self.assertEqual(bill.outstanding_amount, Decimal("500.0000"))
