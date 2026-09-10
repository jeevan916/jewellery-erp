from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from apps.inventory.models import InventoryTransaction, Item, StockLot

ZERO_W = Decimal("0.000000")
ZERO_M = Decimal("0.0000")
IN_TYPES = {
    InventoryTransaction.TransactionType.RECEIPT,
    InventoryTransaction.TransactionType.ADJUSTMENT_IN,
    InventoryTransaction.TransactionType.TRANSFER_IN,
}


def _weight(value):
    return Decimal(str(value)).quantize(Decimal("0.000001"))


def _money(value):
    return Decimal(str(value)).quantize(Decimal("0.0001"))


@transaction.atomic
def record_transaction(*, item_id, lot_id, transaction_type, transaction_date, quantity=0, gross_weight=0, net_weight=0, fine_weight=0, value=0, reference_type="", reference_id="", reference_number="", narration=""):
    item = Item.objects.select_for_update().get(pk=item_id)
    lot = StockLot.objects.select_for_update().get(pk=lot_id)
    if lot.item_id != item.id:
        raise ValidationError("Stock lot does not belong to the item.")
    if not item.is_active or not lot.is_active:
        raise ValidationError("Item and stock lot must be active.")
    quantity = _weight(quantity)
    gross_weight = _weight(gross_weight)
    net_weight = _weight(net_weight)
    fine_weight = _weight(fine_weight)
    value = _money(value)
    if quantity < 0 or gross_weight < 0 or net_weight < 0 or fine_weight < 0 or value < 0:
        raise ValidationError("Inventory quantities, weights and value cannot be negative.")
    if net_weight > gross_weight:
        raise ValidationError("Net weight cannot exceed gross weight.")
    if fine_weight > net_weight:
        raise ValidationError("Fine weight cannot exceed net weight.")
    current = lot_balance(lot_id=lot.id)
    if transaction_type not in IN_TYPES and (
        quantity > current["quantity"] or net_weight > current["net_weight"] or fine_weight > current["fine_weight"]
    ):
        raise ValidationError("Insufficient stock for this inventory issue.")
    return InventoryTransaction.objects.create(
        item=item,
        lot=lot,
        transaction_type=transaction_type,
        transaction_date=transaction_date,
        quantity=quantity,
        gross_weight=gross_weight,
        net_weight=net_weight,
        fine_weight=fine_weight,
        value=value,
        reference_type=reference_type,
        reference_id=reference_id,
        reference_number=reference_number,
        narration=narration,
    )


def lot_balance(*, lot_id):
    qs = InventoryTransaction.objects.filter(lot_id=lot_id)
    result = {"quantity": ZERO_W, "gross_weight": ZERO_W, "net_weight": ZERO_W, "fine_weight": ZERO_W, "value": ZERO_M}
    for field, zero in (("quantity", ZERO_W), ("gross_weight", ZERO_W), ("net_weight", ZERO_W), ("fine_weight", ZERO_W), ("value", ZERO_M)):
        incoming = qs.filter(transaction_type__in=IN_TYPES).aggregate(v=Sum(field))["v"] or zero
        outgoing = qs.exclude(transaction_type__in=IN_TYPES).aggregate(v=Sum(field))["v"] or zero
        result[field] = incoming - outgoing
    return result


def item_balance(*, item_id):
    qs = InventoryTransaction.objects.filter(item_id=item_id)
    result = {"quantity": ZERO_W, "gross_weight": ZERO_W, "net_weight": ZERO_W, "fine_weight": ZERO_W, "value": ZERO_M}
    for field, zero in (("quantity", ZERO_W), ("gross_weight", ZERO_W), ("net_weight", ZERO_W), ("fine_weight", ZERO_W), ("value", ZERO_M)):
        incoming = qs.filter(transaction_type__in=IN_TYPES).aggregate(v=Sum(field))["v"] or zero
        outgoing = qs.exclude(transaction_type__in=IN_TYPES).aggregate(v=Sum(field))["v"] or zero
        result[field] = incoming - outgoing
    return result
