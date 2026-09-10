from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from apps.accounting.models import (
    Account,
    BillReference,
    FinancialPeriod,
    Party,
    Payment,
    PaymentAllocation,
    Voucher,
    VoucherType,
)
from apps.accounting.services.posting import post_voucher

ZERO = Decimal("0.0000")


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.0001"))


def active_account(pk):
    account = Account.objects.filter(pk=pk, is_active=True).first()
    if not account:
        raise ValidationError("Account is missing or inactive.")
    return account


def create_payment(*, party_id, payment_type, voucher_number, payment_date, amount, account_id, reference="", narration=""):
    amount = money(amount)
    if amount <= ZERO:
        raise ValidationError("Payment amount must be positive.")
    party = Party.objects.get(pk=party_id)
    expected = Party.PartyType.CUSTOMER if payment_type == Payment.PaymentType.RECEIPT else Party.PartyType.SUPPLIER
    if party.party_type != expected:
        raise ValidationError("Party type does not match payment type.")
    active_account(account_id)
    with transaction.atomic():
        code = "RECEIPT" if payment_type == Payment.PaymentType.RECEIPT else "PAYMENT"
        vt, _ = VoucherType.objects.get_or_create(
            code=code,
            defaults={"name": code.title(), "category": code, "prefix": "RCPT" if code == "RECEIPT" else "PAY"},
        )
        voucher = Voucher.objects.create(
            voucher_type=vt,
            number=voucher_number,
            voucher_date=payment_date,
            status=Voucher.Status.DRAFT,
            reference=reference,
            narration=narration,
        )
        return Payment.objects.create(
            party=party,
            voucher=voucher,
            payment_date=payment_date,
            payment_type=payment_type,
            amount=amount,
            reference=reference,
            narration=narration,
        )


@transaction.atomic
def post_payment(*, payment_id, financial_period_id, account_id):
    payment = Payment.objects.select_for_update().select_related("party").get(pk=payment_id)
    if payment.status != Payment.Status.DRAFT:
        raise ValidationError("Only a draft payment can be posted.")
    FinancialPeriod.objects.select_for_update().get(pk=financial_period_id)
    active_account(account_id)
    party_account = active_account(payment.party.account_id)
    if payment.payment_type == Payment.PaymentType.RECEIPT:
        lines = [
            {"account_id": account_id, "debit": payment.amount, "narration": payment.reference or "Receipt"},
            {"account_id": party_account.id, "credit": payment.amount, "narration": payment.reference or "Receipt"},
        ]
    else:
        lines = [
            {"account_id": party_account.id, "debit": payment.amount, "narration": payment.reference or "Payment"},
            {"account_id": account_id, "credit": payment.amount, "narration": payment.reference or "Payment"},
        ]
    entry = post_voucher(voucher_id=payment.voucher_id, lines=lines, period_id=financial_period_id)
    payment.status = Payment.Status.POSTED
    payment.save(update_fields=["status"])
    return payment, entry


def active_allocated(*, payment_id=None, bill_id=None):
    qs = PaymentAllocation.objects.all()
    if payment_id is not None:
        qs = qs.filter(payment_id=payment_id)
    elif bill_id is not None:
        qs = qs.filter(bill_id=bill_id)
    else:
        raise ValueError("payment_id or bill_id is required")
    totals = qs.aggregate(
        allocated=Sum("amount", filter=__import__("django.db.models", fromlist=["Q"]).Q(entry_type=PaymentAllocation.EntryType.ALLOCATE)),
        deallocated=Sum("amount", filter=__import__("django.db.models", fromlist=["Q"]).Q(entry_type=PaymentAllocation.EntryType.DEALLOCATE)),
    )
    return max((totals["allocated"] or ZERO) - (totals["deallocated"] or ZERO), ZERO)


@transaction.atomic
def allocate_payment(*, payment_id, bill_id, amount):
    amount = money(amount)
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    bill = BillReference.objects.select_for_update().get(pk=bill_id)
    if payment.status != Payment.Status.POSTED:
        raise ValidationError("Only a posted payment can be allocated.")
    if payment.party_id != bill.party_id:
        raise ValidationError("Payment and bill must belong to the same party.")
    expected = BillReference.BillType.RECEIVABLE if payment.payment_type == Payment.PaymentType.RECEIPT else BillReference.BillType.PAYABLE
    if bill.bill_type != expected:
        raise ValidationError("Bill type does not match payment type.")
    available_payment = payment.amount - active_allocated(payment_id=payment.id)
    available_bill = bill.amount - active_allocated(bill_id=bill.id)
    if amount <= ZERO or amount > available_payment or amount > available_bill:
        raise ValidationError(f"Allocation exceeds available amount. Payment={available_payment}, Bill={available_bill}.")
    allocation = PaymentAllocation.objects.create(
        payment=payment,
        bill=bill,
        entry_type=PaymentAllocation.EntryType.ALLOCATE,
        amount=amount,
    )
    BillReference.objects.filter(pk=bill.pk).update(
        status=BillReference.Status.SETTLED if available_bill == amount else BillReference.Status.OPEN
    )
    return allocation


@transaction.atomic
def deallocate_payment(*, allocation_id, amount=None):
    allocation = PaymentAllocation.objects.select_for_update().select_related("payment", "bill").get(pk=allocation_id)
    if allocation.entry_type != PaymentAllocation.EntryType.ALLOCATE:
        raise ValidationError("Only an allocation can be deallocated.")
    released = PaymentAllocation.objects.filter(
        reference_allocation_id=allocation.id,
        entry_type=PaymentAllocation.EntryType.DEALLOCATE,
    ).aggregate(v=Sum("amount"))["v"] or ZERO
    remaining = allocation.amount - released
    amount = remaining if amount is None else money(amount)
    if amount <= ZERO or amount > remaining:
        raise ValidationError("Invalid deallocation amount.")
    reversal = PaymentAllocation.objects.create(
        payment_id=allocation.payment_id,
        bill_id=allocation.bill_id,
        entry_type=PaymentAllocation.EntryType.DEALLOCATE,
        amount=amount,
        reference_allocation=allocation,
    )
    # Recalculate the bill's active allocation after the append-only reversal.
    active_bill_allocation = active_allocated(bill_id=allocation.bill_id)
    bill_status = BillReference.Status.SETTLED if active_bill_allocation == allocation.bill.amount else BillReference.Status.OPEN
    BillReference.objects.filter(pk=allocation.bill_id).update(status=bill_status)
    return reversal
