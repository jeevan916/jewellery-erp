from decimal import Decimal

from django.db.models import F, Sum

from apps.accounting.models import Account, AccountGroup, JournalEntryLine

ZERO = Decimal("0.0000")


def _line_totals(*, start_date=None, end_date=None):
    lines = JournalEntryLine.objects.filter(journal_entry__status="POSTED")
    if start_date is not None:
        lines = lines.filter(journal_entry__entry_date__gte=start_date)
    if end_date is not None:
        lines = lines.filter(journal_entry__entry_date__lte=end_date)
    return lines.values("account_id").annotate(
        debit=Sum("debit"),
        credit=Sum("credit"),
    )


def trial_balance(*, start_date=None, end_date=None):
    """Return account-wise trial balance derived entirely from posted journal lines."""
    totals = {
        row["account_id"]: (
            row["debit"] or ZERO,
            row["credit"] or ZERO,
        )
        for row in _line_totals(start_date=start_date, end_date=end_date)
    }
    accounts = Account.objects.filter(id__in=totals).select_related("group").order_by("code")
    rows = []
    total_debit = ZERO
    total_credit = ZERO
    for account in accounts:
        debit, credit = totals[account.id]
        total_debit += debit
        total_credit += credit
        rows.append({
            "account_id": account.id,
            "code": account.code,
            "name": account.name,
            "group_code": account.group.code,
            "group_name": account.group.name,
            "debit": debit,
            "credit": credit,
        })
    return {
        "rows": rows,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "balanced": total_debit == total_credit,
    }


def profit_and_loss(*, start_date=None, end_date=None):
    """Return income and expense totals using account-group nature."""
    tb = trial_balance(start_date=start_date, end_date=end_date)
    income = ZERO
    expense = ZERO
    rows = []
    for row in tb["rows"]:
        if AccountGroup.objects.filter(code=row["group_code"], nature=AccountGroup.Nature.INCOME).exists():
            amount = row["credit"] - row["debit"]
            income += amount
            if amount:
                rows.append({**row, "classification": "INCOME", "amount": amount})
        elif AccountGroup.objects.filter(code=row["group_code"], nature=AccountGroup.Nature.EXPENSE).exists():
            amount = row["debit"] - row["credit"]
            expense += amount
            if amount:
                rows.append({**row, "classification": "EXPENSE", "amount": amount})
    return {
        "income": income,
        "expense": expense,
        "net_profit": income - expense,
        "rows": rows,
    }


def balance_sheet(*, as_of_date=None):
    """Return asset/liability/equity balances as of a date."""
    tb = trial_balance(end_date=as_of_date)
    assets = ZERO
    liabilities = ZERO
    equity = ZERO
    rows = []
    for row in tb["rows"]:
        group = AccountGroup.objects.get(code=row["group_code"])
        signed = row["debit"] - row["credit"]
        if group.nature == AccountGroup.Nature.ASSET:
            amount = signed
            assets += amount
            classification = "ASSET"
        elif group.nature == AccountGroup.Nature.LIABILITY:
            amount = -signed
            liabilities += amount
            classification = "LIABILITY"
        elif group.nature == AccountGroup.Nature.EQUITY:
            amount = -signed
            equity += amount
            classification = "EQUITY"
        else:
            continue
        if amount:
            rows.append({**row, "classification": classification, "amount": amount})
    return {
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "net_assets": assets - liabilities - equity,
        "rows": rows,
    }
