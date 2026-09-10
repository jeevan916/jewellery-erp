from decimal import Decimal

from django.db.models import Sum

from apps.accounting.models import Account, JournalEntryLine


ZERO = Decimal("0.0000")


def _signed_balance(debit: Decimal, credit: Decimal) -> Decimal:
    """Return the ledger running balance as debit-positive / credit-negative."""
    return (debit or ZERO) - (credit or ZERO)


def _side(balance: Decimal) -> str:
    if balance > ZERO:
        return "DR"
    if balance < ZERO:
        return "CR"
    return "ZERO"


def account_ledger(*, account_id: int, start_date=None, end_date=None):
    """Return chronological Tally-style ledger rows with a running balance.

    Journal entries are the only source of truth. No balance is stored on Account.
    """
    Account.objects.get(pk=account_id)
    lines = JournalEntryLine.objects.filter(
        account_id=account_id,
        journal_entry__status="POSTED",
    ).select_related("journal_entry__voucher__voucher_type").order_by(
        "journal_entry__entry_date", "journal_entry_id", "line_no"
    )

    if start_date is not None:
        lines = lines.filter(journal_entry__entry_date__gte=start_date)
    if end_date is not None:
        lines = lines.filter(journal_entry__entry_date__lte=end_date)

    opening = ZERO
    if start_date is not None:
        opening_totals = JournalEntryLine.objects.filter(
            account_id=account_id,
            journal_entry__status="POSTED",
            journal_entry__entry_date__lt=start_date,
        ).aggregate(debit=Sum("debit"), credit=Sum("credit"))
        opening = _signed_balance(opening_totals["debit"] or ZERO, opening_totals["credit"] or ZERO)

    balance = opening
    rows = []
    for line in lines:
        balance += _signed_balance(line.debit, line.credit)
        rows.append({
            "date": line.journal_entry.entry_date,
            "voucher_id": line.journal_entry.voucher_id,
            "voucher_number": line.journal_entry.voucher.number,
            "voucher_type": line.journal_entry.voucher.voucher_type.code,
            "line_no": line.line_no,
            "debit": line.debit,
            "credit": line.credit,
            "narration": line.narration or line.journal_entry.voucher.narration,
            "balance": abs(balance),
            "balance_side": _side(balance),
        })

    return {
        "account_id": account_id,
        "opening_balance": abs(opening),
        "opening_side": _side(opening),
        "rows": rows,
        "closing_balance": abs(balance),
        "closing_side": _side(balance),
    }


def account_t_shape(*, account_id: int, start_date=None, end_date=None):
    """Return debit and credit sides for a classic T-account view."""
    ledger = account_ledger(account_id=account_id, start_date=start_date, end_date=end_date)
    debit = [row for row in ledger["rows"] if row["debit"] > ZERO]
    credit = [row for row in ledger["rows"] if row["credit"] > ZERO]
    return {
        "account_id": account_id,
        "opening_balance": ledger["opening_balance"],
        "opening_side": ledger["opening_side"],
        "debit": debit,
        "credit": credit,
        "closing_balance": ledger["closing_balance"],
        "closing_side": ledger["closing_side"],
    }
