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


def get_bill_outstanding(bill_id: int) -> Decimal:
    bill = BillReference.objects.get(pk=bill_id)
    allocated = bill.allocations.filter(payment__status=Payment.Status.POSTED).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.0000")
    return max(bill.amount - allocated, Decimal("0.0000"))


def get_payment_unallocated(payment_id: int) -> Decimal:
    payment = Payment.objects.get(pk=payment_id)
    allocated = payment.allocations.filter(payment__status=Payment.Status.POSTED).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.0000")
    return max(payment.amount - allocated, Decimal("0.0000"))


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

    allocated_payment = payment.allocations.filter(payment__status=Payment.Status.POSTED).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.0000")
    allocated_bill = bill.allocations.filter(payment__status=Payment.Status.POSTED).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.0000")

    payment_available = payment.amount - allocated_payment
    bill_outstanding = bill.amount - allocated_bill

    if amount > payment_available:
        raise BillWiseError(
            f"Allocation exceeds payment's unallocated amount ({payment_available:.4f})."
        )
    if amount > bill_outstanding:
        raise BillWiseError(
            f"Allocation exceeds bill's outstanding amount ({bill_outstanding:.4f})."
        )

    allocation, created = PaymentAllocation.objects.get_or_create(
        payment=payment,
        bill=bill,
        defaults={"amount": amount},
    )
    if not created:
        new_amount = allocation.amount + amount
        allocation.amount = new_amount
        allocation.full_clean()
        allocation.save(update_fields=["amount"])

    new_bill_outstanding = bill_outstanding - amount
    bill.status = (
        BillReference.Status.SETTLED
        if new_bill_outstanding == 0
        else BillReference.Status.OPEN
    )
    bill.save(update_fields=["status"])

    return allocation


@transaction.atomic
def deallocate_payment(*, allocation_id: int, amount=None) -> PaymentAllocation | None:
    """Reverse an allocation without deleting financial history."""
    allocation = PaymentAllocation.objects.select_for_update().select_related(
        "payment", "bill"
    ).get(pk=allocation_id)
    payment = Payment.objects.select_for_update().get(pk=allocation.payment_id)
    bill = BillReference.objects.select_for_update().get(pk=allocation.bill_id)

    if amount is None:
        release = allocation.amount
    else:
        release = _money(amount)
        if release > allocation.amount:
            raise BillWiseError("Deallocation exceeds the existing allocation.")

    remaining = allocation.amount - release
    if remaining == 0:
        allocation.delete()
        result = None
    else:
        allocation.amount = remaining
        allocation.save(update_fields=["amount"])
        result = allocation

    bill.status = BillReference.Status.OPEN
    bill.save(update_fields=["status"])
    return result


def party_outstanding(*, party_id: int) -> Decimal:
    """Return positive receivable/payable outstanding for a party."""
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
