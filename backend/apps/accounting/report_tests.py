from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.accounting.models import Account, AccountGroup, FinancialPeriod, JournalEntry, JournalEntryLine, Voucher, VoucherType
from apps.accounting.services.reports import balance_sheet, profit_and_loss, trial_balance


class FinancialReportTests(TestCase):
    def setUp(self):
        assets = AccountGroup.objects.create(code="1000", name="Assets", nature=AccountGroup.Nature.ASSET)
        equity = AccountGroup.objects.create(code="3000", name="Equity", nature=AccountGroup.Nature.EQUITY)
        income = AccountGroup.objects.create(code="4000", name="Sales", nature=AccountGroup.Nature.INCOME)
        expense = AccountGroup.objects.create(code="5000", name="Expenses", nature=AccountGroup.Nature.EXPENSE)
        self.cash = Account.objects.create(code="1001", name="Cash", group=assets)
        self.capital = Account.objects.create(code="3001", name="Capital", group=equity)
        self.sales = Account.objects.create(code="4001", name="Sales", group=income)
        self.expense = Account.objects.create(code="5001", name="Rent", group=expense)
        self.period = FinancialPeriod.objects.create(
            name="2026-27", starts_on=date(2026, 4, 1), ends_on=date(2027, 3, 31)
        )
        self.vtype = VoucherType.objects.create(code="JV", name="Journal", category="JOURNAL")

    def post(self, number, lines, entry_date=date(2026, 9, 10)):
        debit = sum((Decimal(str(line.get("debit", "0"))) for line in lines), Decimal("0"))
        credit = sum((Decimal(str(line.get("credit", "0"))) for line in lines), Decimal("0"))
        voucher = Voucher.objects.create(
            voucher_type=self.vtype, number=number, voucher_date=entry_date,
            status=Voucher.Status.POSTED,
        )
        entry = JournalEntry.objects.create(
            voucher=voucher, financial_period=self.period, entry_date=entry_date,
            total_debit=debit, total_credit=credit,
        )
        for line_no, line in enumerate(lines, start=1):
            JournalEntryLine.objects.create(
                journal_entry=entry, account_id=line["account_id"], line_no=line_no,
                debit=line.get("debit", "0"), credit=line.get("credit", "0"),
            )

    def test_trial_balance_is_balanced(self):
        self.post("1", [
            {"account_id": self.cash.id, "debit": "1000"},
            {"account_id": self.capital.id, "credit": "1000"},
        ])
        tb = trial_balance()
        self.assertTrue(tb["balanced"])
        self.assertEqual(tb["total_debit"], Decimal("1000.0000"))
        self.assertEqual(tb["total_credit"], Decimal("1000.0000"))

    def test_profit_and_loss(self):
        self.post("1", [
            {"account_id": self.cash.id, "debit": "1000"},
            {"account_id": self.sales.id, "credit": "1000"},
        ])
        self.post("2", [
            {"account_id": self.expense.id, "debit": "250"},
            {"account_id": self.cash.id, "credit": "250"},
        ])
        pnl = profit_and_loss(start_date=date(2026, 4, 1), end_date=date(2026, 9, 30))
        self.assertEqual(pnl["income"], Decimal("1000.0000"))
        self.assertEqual(pnl["expense"], Decimal("250.0000"))
        self.assertEqual(pnl["net_profit"], Decimal("750.0000"))

    def test_balance_sheet_balances(self):
        self.post("1", [
            {"account_id": self.cash.id, "debit": "1000"},
            {"account_id": self.capital.id, "credit": "1000"},
        ])
        bs = balance_sheet(as_of_date=date(2026, 9, 30))
        self.assertEqual(bs["assets"], Decimal("1000.0000"))
        self.assertEqual(bs["liabilities"], Decimal("0.0000"))
        self.assertEqual(bs["equity"], Decimal("1000.0000"))
        self.assertEqual(bs["net_assets"], Decimal("0.0000"))
