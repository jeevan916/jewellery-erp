from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum

from .core import Account
from .journal import Voucher


class Party(models.Model):
    class PartyType(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        SUPPLIER = "SUPPLIER", "Supplier"

    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=180)
    party_type = models.CharField(max_length=10, choices=PartyType.choices)
    account = models.OneToOneField(Account, on_delete=models.PROTECT, related_name="party")
    gstin = models.CharField(max_length=15, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        indexes = [models.Index(fields=["party_type", "is_active"])]

    def clean(self):
        if not self.account.is_party_account:
            raise ValidationError("Party account must be marked as a party account.")
        if not self.account.is_active:
            raise ValidationError("Party account must be active.")

    def __str__(self):
        return f"{self.code} - {self.name}"


class BillReference(models.Model):
    class BillType(models.TextChoices):
        RECEIVABLE = "RECEIVABLE", "Receivable"
        PAYABLE = "PAYABLE", "Payable"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        SETTLED = "SETTLED", "Settled"
        CANCELLED = "CANCELLED", "Cancelled"

    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name="bills")
    voucher = models.OneToOneField(Voucher, on_delete=models.PROTECT, related_name="bill_reference")
    bill_number = models.CharField(max_length=80)
    bill_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    bill_type = models.CharField(max_length=12, choices=BillType.choices)
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    narration = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["party", "bill_number"], name="uq_party_bill_number"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="bill_amount_positive"),
        ]
        indexes = [
            models.Index(fields=["party", "status", "bill_date"]),
            models.Index(fields=["due_date", "status"]),
        ]
        ordering = ["bill_date", "id"]

    @property
    def allocated_amount(self):
        return self.allocations.filter(payment__status=Payment.Status.POSTED).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.0000")

    @property
    def outstanding_amount(self):
        return max(self.amount - self.allocated_amount, Decimal("0.0000"))

    def __str__(self):
        return f"{self.party.code} / {self.bill_number}"


class Payment(models.Model):
    class PaymentType(models.TextChoices):
        RECEIPT = "RECEIPT", "Receipt"
        PAYMENT = "PAYMENT", "Payment"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"
        REVERSED = "REVERSED", "Reversed"

    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name="payments")
    voucher = models.OneToOneField(Voucher, on_delete=models.PROTECT, related_name="payment")
    payment_date = models.DateField()
    payment_type = models.CharField(max_length=10, choices=PaymentType.choices)
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    reference = models.CharField(max_length=120, blank=True)
    narration = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive")]
        indexes = [models.Index(fields=["party", "payment_date", "status"])]
        ordering = ["payment_date", "id"]

    @property
    def allocated_amount(self):
        return self.allocations.filter(payment__status=self.Status.POSTED).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.0000")

    @property
    def unallocated_amount(self):
        return max(self.amount - self.allocated_amount, Decimal("0.0000"))


class PaymentAllocation(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="allocations")
    bill = models.ForeignKey(BillReference, on_delete=models.PROTECT, related_name="allocations")
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    allocated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["payment", "bill"], name="uq_payment_bill_allocation"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="allocation_amount_positive"),
        ]
        indexes = [models.Index(fields=["bill", "payment"])]

    def clean(self):
        if self.payment_id and self.bill_id and self.payment.party_id != self.bill.party_id:
            raise ValidationError("Payment and bill must belong to the same party.")

    def __str__(self):
        return f"{self.payment_id} -> {self.bill_id}: {self.amount}"
