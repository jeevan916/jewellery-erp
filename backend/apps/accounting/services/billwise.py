from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from apps.accounting.models import BillReference, Party, Payment, PaymentAllocation


class BillWiseError(ValidationError):
    """Raised when a bill-wise accounting operation violates an invariant."""


def _money(value) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise BillWiseError("Amount must be a valid decimal value.") from exc
    if amount <= 0:
        raise BillWiseError("Amount must be greater than zero.")
    return amount.quantize(Decimal("0.0001"))


def _net_allocated(queryset) -> Decimal:
    allocated = queryset.filter(entry_type=PaymentAllocation.EntryType.ALLOCATE).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.0000")
    released = queryset.filter(entry_type=PaymentAllocation.EntryType.DEALLOCATE).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.0000")
    return max(allocated - released, Decimal("0.0000"))


def get_bill_outstanding(bill_id: int) -> Decimal:
    bill = BillReference.objects.get(pk=bill_id)
    return max(bill.amount - _net_allocated(bill.allocations.all()), Decimal("0.0000"))


def get_payment_unallocated(payment_id: int) -> Decimal:
    payment = Payment.objects.get(pk=payment_id)
    return max(payment.amount - _net_allocated(payment.allocations.all()), Decimal("0.0000"))


@transaction.atomic
def allocate_payment(*, payment_id: int, bill_id: int, amount) -> PaymentAllocation:
    """Allocate a posted receipt/payment to a bill with concurrency protection."""
    amount = _money(amount)

    payment = Payment.objects.select_for_update().select_related("party").get(pk=payment_id)
    bill = BillReference.objects.select_for_update().select_related("party").get(pk=bill_id)

    if payment.status != Payment.Status.POSTED:
        raise BillWiseError("Only posted payments can be allocated.")
    if bill.status == BillReference.Status.CANCELLED:
        raise BillWiseError("A cancelled bill cannot receive an allocation.")
    if payment.party_id != bill.party_id:
        raise BillWiseError("Payment and bill must belong to the same party.")

    expected_bill_type = (
        BillReference.BillType.RECEIVABLE
        if payment.payment_type == Payment.PaymentType.RECEIPT
        else BillReference.BillType.PAYABLE
    )
    if bill.bill_type != expected_bill_type:
        raise BillWiseError("Receipt must be allocated to a receivable bill and payment to a payable bill.")

    payment_available = payment.amount - _net_allocated(payment.allocations.all())
    bill_outstanding = bill.amount - _net_allocated(bill.allocations.all())

    if amount > payment_available:
        raise BillWiseError(
            f"Allocation exceeds payment's unallocated amount ({payment_available:.4f})."
        )
    if amount > bill_outstanding:
        raise BillWiseError(
            f"Allocation exceeds bill's outstanding amount ({bill_outstanding:.4f})."
        )

    allocation = PaymentAllocation.objects.create(
        payment=payment,
        bill=bill,
        entry_type=PaymentAllocation.EntryType.ALLOCATE,
        amount=amount,
    )
    allocation.full_clean()

    new_bill_outstanding = bill_outstanding - amount
    bill.status = (
        BillReference.Status.SETTLED
        if new_bill_outstanding == 0
        else BillReference.Status.OPEN
    )
    bill.save(update_fields=["status"])

    return allocation


@transaction.atomic
def deallocate_payment(*, allocation_id: int, amount=None) -> PaymentAllocation:
    """Append a reversal entry; the original allocation is never deleted or edited."""
    allocation = PaymentAllocation.objects.select_for_update().select_related("payment", "bill").get(pk=allocation_id)
    payment = Payment.objects.select_for_update().get(pk=allocation.payment_id)
    bill = BillReference.objects.select_for_update().get(pk=allocation.bill_id)

    if allocation.entry_type != PaymentAllocation.EntryType.ALLOCATE:
        raise BillWiseError("Only an allocation entry can be deallocated.")
    if amount is None:
        release = allocation.amount
    else:
        release = _money(amount)

    already_reversed = PaymentAllocation.objects.filter(
        reference_allocation=allocation,
        entry_type=PaymentAllocation.EntryType.DEALLOCATE,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.0000")
    remaining_reversible = allocation.amount - already_reversed
    if release > remaining_reversible:
        raise BillWiseError("Deallocation exceeds the unreversed allocation amount.")

    reversal = PaymentAllocation.objects.create(
        payment=payment,
        bill=bill,
        entry_type=PaymentAllocation.EntryType.DEALLOCATE,
        amount=release,
        reference_allocation=allocation,
    )
    reversal.full_clean()
    bill.status = BillReference.Status.OPEN
    bill.save(update_fields=["status"])
    return reversal


def party_outstanding(*, party_id: int) -> Decimal:
    """Return receivable outstanding minus payable outstanding for a party."""
    Party.objects.get(pk=party_id)
    receivable = sum(
        (get_bill_outstanding(bill.id) for bill in BillReference.objects.filter(
            party_id=party_id,
            bill_type=BillReference.BillType.RECEIVABLE,
            status__in=[BillReference.Status.OPEN, BillReference.Status.SETTLED],
        )),
        Decimal("0.0000"),
    )
    payable = sum(
        (get_bill_outstanding(bill.id) for bill in BillReference.objects.filter(
            party_id=party_id,
            bill_type=BillReference.BillType.PAYABLE,
            status__in=[BillReference.Status.OPEN, BillReference.Status.SETTLED],
        )),
        Decimal("0.0000"),
    )
    return receivable - payable
