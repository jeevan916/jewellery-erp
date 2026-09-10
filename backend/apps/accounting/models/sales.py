from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .billwise import Party
from .journal import Voucher


class SalesInvoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"
        REVERSED = "REVERSED", "Reversed"
        CANCELLED = "CANCELLED", "Cancelled"

    customer = models.ForeignKey(Party, on_delete=models.PROTECT, related_name="sales_invoices")
    voucher = models.OneToOneField(Voucher, on_delete=models.PROTECT, related_name="sales_invoice")
    invoice_number = models.CharField(max_length=80)
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    taxable_value = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    cgst = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    sgst = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    igst = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    discount = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    total_amount = models.DecimalField(max_digits=19, decimal_places=4)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    narration = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["customer", "invoice_number"], name="uq_customer_sales_invoice"),
            models.CheckConstraint(condition=Q(total_amount__gt=0), name="sales_invoice_total_positive"),
        ]
        indexes = [models.Index(fields=["invoice_date", "customer", "status"])]
        ordering = ["-invoice_date", "-id"]

    def clean(self):
        if self.customer.party_type != Party.PartyType.CUSTOMER:
            raise ValidationError("Sales invoice customer must be a customer party.")
        calculated = self.taxable_value + self.cgst + self.sgst + self.igst
        if calculated != self.total_amount:
            raise ValidationError("Sales invoice total must equal taxable value plus GST.")

    def __str__(self):
        return self.invoice_number


class SalesInvoiceLine(models.Model):
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.PROTECT, related_name="lines")
    line_no = models.PositiveIntegerField()
    description = models.CharField(max_length=255)
    hsn_code = models.CharField(max_length=20, blank=True)
    quantity = models.DecimalField(max_digits=19, decimal_places=6)
    rate = models.DecimalField(max_digits=19, decimal_places=4)
    discount = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    taxable_value = models.DecimalField(max_digits=19, decimal_places=4)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["invoice", "line_no"], name="uq_sales_invoice_line_no"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="sales_line_quantity_positive"),
            models.CheckConstraint(condition=Q(rate__gte=0), name="sales_line_rate_nonnegative"),
            models.CheckConstraint(condition=Q(taxable_value__gte=0), name="sales_line_taxable_nonnegative"),
        ]

    def clean(self):
        expected = (self.quantity * self.rate - self.discount).quantize(Decimal("0.0001"))
        if expected != self.taxable_value:
            raise ValidationError("Sales line taxable value does not match quantity, rate and discount.")
