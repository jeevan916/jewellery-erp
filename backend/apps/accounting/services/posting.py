from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounting.models import Account, FinancialPeriod, JournalEntry, JournalEntryLine, Voucher


class PostingError(ValidationError):
    pass


@transaction.atomic
def post_voucher(*, voucher_id: int, lines: list[dict], period_id: int) -> JournalEntry:
    voucher = Voucher.objects.select_for_update().select_related("voucher_type").get(pk=voucher_id)
    period = FinancialPeriod.objects.select_for_update().get(pk=period_id)

    if voucher.status != Voucher.Status.DRAFT:
        raise PostingError("Only draft vouchers can be posted.")
    if period.status != FinancialPeriod.Status.OPEN:
        raise PostingError("The financial period is not open.")
    if not (period.starts_on <= voucher.voucher_date <= period.ends_on):
        raise PostingError("Voucher date is outside the selected financial period.")
    if len(lines) < 2:
        raise PostingError("A journal entry requires at least two lines.")

    total_debit = Decimal("0.0000")
    total_credit = Decimal("0.0000")
    normalized = []
    account_ids = set()
    for index, item in enumerate(lines, start=1):
        try:
            debit = Decimal(str(item.get("debit", "0")))
            credit = Decimal(str(item.get("credit", "0")))
        except Exception as exc:
            raise PostingError(f"Invalid amount on journal line {index}.") from exc
        if debit < 0 or credit < 0 or (debit > 0 and credit > 0) or (debit == 0 and credit == 0):
            raise PostingError(f"Invalid journal line {index}.")
        account_id = item.get("account_id")
        if not account_id:
            raise PostingError(f"Account is required on journal line {index}.")
        normalized.append((account_id, debit, credit, item.get("narration", "")))
        account_ids.add(account_id)
        total_debit += debit
        total_credit += credit

    if total_debit != total_credit or total_debit <= 0:
        raise PostingError("Journal entry must have equal, positive debit and credit totals.")

    locked_accounts = list(
        Account.objects.select_for_update().filter(id__in=account_ids)
    )
    active_ids = {account.id for account in locked_accounts if account.is_active}
    missing_or_inactive = account_ids - active_ids
    if missing_or_inactive:
        raise PostingError(
            f"Journal entry contains missing or inactive account(s): {sorted(missing_or_inactive)}"
        )

    entry = JournalEntry.objects.create(
        voucher=voucher,
        financial_period=period,
        entry_date=voucher.voucher_date,
        status=JournalEntry.Status.POSTED,
        total_debit=total_debit,
        total_credit=total_credit,
    )
    JournalEntryLine.objects.bulk_create([
        JournalEntryLine(
            journal_entry=entry,
            account_id=account_id,
            line_no=index,
            debit=debit,
            credit=credit,
            narration=narration,
        )
        for index, (account_id, debit, credit, narration) in enumerate(normalized, start=1)
    ])
    voucher.status = Voucher.Status.POSTED
    voucher.posted_at = timezone.now()
    voucher.save(update_fields=["status", "posted_at"])
    return entry
