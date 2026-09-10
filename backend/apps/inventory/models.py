from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class MetalType(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Purity(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=80)
    fineness = models.DecimalField(max_digits=10, decimal_places=6)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["fineness", "code"]
        constraints = [
            models.CheckConstraint(condition=Q(fineness__gt=0, fineness__lte=1), name="purity_fineness_0_1"),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Item(models.Model):
    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=180)
    metal_type = models.ForeignKey(MetalType, on_delete=models.PROTECT, related_name="items")
    purity = models.ForeignKey(Purity, on_delete=models.PROTECT, related_name="items", null=True, blank=True)
    hsn_code = models.CharField(max_length=20, blank=True)
    unit = models.CharField(max_length=20, default="PCS")
    track_weight = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(fields=["metal_type", "purity", "is_active"], name="inventory_item_metal_purity_idx"),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class StockLot(models.Model):
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="lots")
    lot_number = models.CharField(max_length=80, unique=True)
    tag_number = models.CharField(max_length=80, blank=True)
    huid = models.CharField(max_length=20, blank=True)
    gross_weight = models.DecimalField(max_digits=19, decimal_places=6, default=Decimal("0"))
    net_weight = models.DecimalField(max_digits=19, decimal_places=6, default=Decimal("0"))
    fine_weight = models.DecimalField(max_digits=19, decimal_places=6, default=Decimal("0"))
    cost_value = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["item", "is_active"], name="inventory_lot_item_active_idx"),
            models.Index(fields=["tag_number"], name="inventory_lot_tag_idx"),
            models.Index(fields=["huid"], name="inventory_lot_huid_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(gross_weight__gte=0), name="stock_lot_gross_nonnegative"),
            models.CheckConstraint(condition=Q(net_weight__gte=0), name="stock_lot_net_nonnegative"),
            models.CheckConstraint(condition=Q(fine_weight__gte=0), name="stock_lot_fine_nonnegative"),
            models.CheckConstraint(condition=Q(cost_value__gte=0), name="stock_lot_cost_nonnegative"),
        ]

    def clean(self):
        if self.net_weight > self.gross_weight:
            raise ValidationError("Net weight cannot exceed gross weight.")
        if self.fine_weight > self.net_weight:
            raise ValidationError("Fine weight cannot exceed net weight.")

    def __str__(self):
        return self.lot_number


class InventoryTransaction(models.Model):
    class TransactionType(models.TextChoices):
        RECEIPT = "RECEIPT", "Receipt"
        ISSUE = "ISSUE", "Issue"
        ADJUSTMENT_IN = "ADJUSTMENT_IN", "Adjustment In"
        ADJUSTMENT_OUT = "ADJUSTMENT_OUT", "Adjustment Out"
        TRANSFER_IN = "TRANSFER_IN", "Transfer In"
        TRANSFER_OUT = "TRANSFER_OUT", "Transfer Out"

    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    transaction_date = models.DateField()
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="inventory_transactions")
    lot = models.ForeignKey(StockLot, on_delete=models.PROTECT, related_name="transactions")
    quantity = models.DecimalField(max_digits=19, decimal_places=6, default=Decimal("0"))
    gross_weight = models.DecimalField(max_digits=19, decimal_places=6, default=Decimal("0"))
    net_weight = models.DecimalField(max_digits=19, decimal_places=6, default=Decimal("0"))
    fine_weight = models.DecimalField(max_digits=19, decimal_places=6, default=Decimal("0"))
    value = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0.0000"))
    reference_type = models.CharField(max_length=40, blank=True)
    reference_id = models.CharField(max_length=80, blank=True)
    reference_number = models.CharField(max_length=80, blank=True)
    narration = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["transaction_date", "id"]
        indexes = [
            models.Index(fields=["item", "transaction_date", "id"], name="inventory_tx_item_date_idx"),
            models.Index(fields=["lot", "transaction_date", "id"], name="inventory_tx_lot_date_idx"),
            models.Index(fields=["reference_type", "reference_id"], name="inventory_tx_reference_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=0), name="inventory_tx_qty_nonnegative"),
            models.CheckConstraint(condition=Q(gross_weight__gte=0), name="inventory_tx_gross_nonnegative"),
            models.CheckConstraint(condition=Q(net_weight__gte=0), name="inventory_tx_net_nonnegative"),
            models.CheckConstraint(condition=Q(fine_weight__gte=0), name="inventory_tx_fine_nonnegative"),
            models.CheckConstraint(condition=Q(value__gte=0), name="inventory_tx_value_nonnegative"),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Inventory transactions are immutable; create a reversing transaction instead.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Inventory transactions are immutable and cannot be deleted.")

    @property
    def signed_quantity(self):
        return self.quantity if self.transaction_type in {
            self.TransactionType.RECEIPT,
            self.TransactionType.ADJUSTMENT_IN,
            self.TransactionType.TRANSFER_IN,
        } else -self.quantity

    @property
    def signed_net_weight(self):
        return self.net_weight if self.transaction_type in {
            self.TransactionType.RECEIPT,
            self.TransactionType.ADJUSTMENT_IN,
            self.TransactionType.TRANSFER_IN,
        } else -self.net_weight

    @property
    def signed_fine_weight(self):
        return self.fine_weight if self.transaction_type in {
            self.TransactionType.RECEIPT,
            self.TransactionType.ADJUSTMENT_IN,
            self.TransactionType.TRANSFER_IN,
        } else -self.fine_weight
