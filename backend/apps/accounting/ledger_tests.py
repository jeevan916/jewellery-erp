from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.accounting.models import Account, AccountGroup, FinancialPeriod, JournalEntry, JournalEntryLine, Voucher, VoucherType
from apps.accounting.services.ledger import account_ledger, account_t_shape


class LedgerQueryTests(TestCase):
    def setUp(self):
        assets = AccountGroup.objects.create(code="1000", name="Assets", nature=AccountGroup.Nature.ASSET)
        income = AccountGroup.objects.create(code="4000", name="Income", nature=AccountGroup.Nature.INCOME)
        self.cash = Account.objects.create(code="1001", name="Cash", group=assets, is_cash=True)
        self.sales = Account.objects.create(code="4001", name="Sales", group=income)
        self.period = FinancialPeriod.objects.create(
            name="2026-27", starts_on=date(2026, 4, 1), ends_on=date(2027, 3, 31)
        )
        self.vtype = VoucherType.objects.create(code="JV", name="Journal", category="JOURNAL")

    def post(self, number, entry_date, cash_debit, sales_credit):
        voucher = Voucher.objects.create(
            voucher_type=self.vtype, number=number, voucher_date=entry_date,
            status=Voucher.Status.POSTED,
        )
        entry = JournalEntry.objects.create(
            voucher=voucher, financial_period=self.period, entry_date=entry_date,
            total_debit=cash_debit, total_credit=sales_credit,
        )
        JournalEntryLine.objects.create(
            journal_entry=entry, account=self.cash, line_no=1, debit=cash_debit,
        )
        JournalEntryLine.objects.create(
            journal_entry=entry, account=self.sales, line_no=2, credit=sales_credit,
        )

    def test_running_balance_and_date_range_opening(self):
        self.post("1", date(2026, 4, 1), Decimal("100.00"), Decimal("100.00"))
        self.post("2", date(2026, 4, 5), Decimal("50.00"), Decimal("50.00"))

        ledger = account_ledger(
            account_id=self.cash.id,
            start_date=date(2026, 4, 5),
            end_date=date(2026, 4, 5),
        )
        self.assertEqual(ledger["opening_balance"], Decimal("100.0000"))
        self.assertEqual(ledger["opening_side"], "DR")
        self.assertEqual(ledger["rows"][0]["balance"], Decimal("150.0000"))
        self.assertEqual(ledger["rows"][0]["balance_side"], "DR")
        self.assertEqual(ledger["closing_balance"], Decimal("150.0000"))

    def test_t_shape_separates_debit_and_credit_lines(self):
        self.post("1", date(2026, 4, 1), Decimal("100.00"), Decimal("100.00"))
        shape = account_t_shape(account_id=self.cash.id)
        self.assertEqual(len(shape["debit"]), 1)
        self.assertEqual(len(shape["credit"]), 0)
