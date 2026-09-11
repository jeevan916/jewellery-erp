from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="MetalType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20, unique=True)),
                ("name", models.CharField(max_length=80)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Purity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20, unique=True)),
                ("name", models.CharField(max_length=80)),
                ("fineness", models.DecimalField(decimal_places=6, max_digits=10)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["fineness", "code"]},
        ),
        migrations.CreateModel(
            name="Item",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=60, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("hsn_code", models.CharField(blank=True, max_length=20)),
                ("unit", models.CharField(default="PCS", max_length=20)),
                ("track_weight", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                ("metal_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="items", to="inventory.metaltype")),
                ("purity", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="items", to="inventory.purity")),
            ],
            options={"ordering": ["code"], "indexes": [models.Index(fields=["metal_type", "purity", "is_active"], name="inv_item_metal_pur_idx")]},
        ),
        migrations.CreateModel(
            name="StockLot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lot_number", models.CharField(max_length=80, unique=True)),
                ("tag_number", models.CharField(blank=True, max_length=80)),
                ("huid", models.CharField(blank=True, max_length=20)),
                ("gross_weight", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=19)),
                ("net_weight", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=19)),
                ("fine_weight", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=19)),
                ("cost_value", models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lots", to="inventory.item")),
            ],
            options={"indexes": [models.Index(fields=["item", "is_active"], name="inventory_lot_item_active_idx"), models.Index(fields=["tag_number"], name="inventory_lot_tag_idx"), models.Index(fields=["huid"], name="inventory_lot_huid_idx")]},
        ),
        migrations.CreateModel(
            name="InventoryTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("transaction_type", models.CharField(choices=[("RECEIPT", "Receipt"), ("ISSUE", "Issue"), ("ADJUSTMENT_IN", "Adjustment In"), ("ADJUSTMENT_OUT", "Adjustment Out"), ("TRANSFER_IN", "Transfer In"), ("TRANSFER_OUT", "Transfer Out")], max_length=20)),
                ("transaction_date", models.DateField()),
                ("quantity", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=19)),
                ("gross_weight", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=19)),
                ("net_weight", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=19)),
                ("fine_weight", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=19)),
                ("value", models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19)),
                ("reference_type", models.CharField(blank=True, max_length=40)),
                ("reference_id", models.CharField(blank=True, max_length=80)),
                ("reference_number", models.CharField(blank=True, max_length=80)),
                ("narration", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_transactions", to="inventory.item")),
                ("lot", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transactions", to="inventory.stocklot")),
            ],
            options={"ordering": ["transaction_date", "id"], "indexes": [models.Index(fields=["item", "transaction_date", "id"], name="inventory_tx_item_date_idx"), models.Index(fields=["lot", "transaction_date", "id"], name="inventory_tx_lot_date_idx"), models.Index(fields=["reference_type", "reference_id"], name="inventory_tx_reference_idx")]},
        ),
        migrations.AddConstraint(model_name="purity", constraint=models.CheckConstraint(condition=Q(fineness__gt=0, fineness__lte=1), name="purity_fineness_0_1")),
        migrations.AddConstraint(model_name="stocklot", constraint=models.CheckConstraint(condition=Q(gross_weight__gte=0), name="stock_lot_gross_nonnegative")),
        migrations.AddConstraint(model_name="stocklot", constraint=models.CheckConstraint(condition=Q(net_weight__gte=0), name="stock_lot_net_nonnegative")),
        migrations.AddConstraint(model_name="stocklot", constraint=models.CheckConstraint(condition=Q(fine_weight__gte=0), name="stock_lot_fine_nonnegative")),
        migrations.AddConstraint(model_name="stocklot", constraint=models.CheckConstraint(condition=Q(cost_value__gte=0), name="stock_lot_cost_nonnegative")),
        migrations.AddConstraint(model_name="inventorytransaction", constraint=models.CheckConstraint(condition=Q(quantity__gte=0), name="inventory_tx_qty_nonnegative")),
        migrations.AddConstraint(model_name="inventorytransaction", constraint=models.CheckConstraint(condition=Q(gross_weight__gte=0), name="inventory_tx_gross_nonnegative")),
        migrations.AddConstraint(model_name="inventorytransaction", constraint=models.CheckConstraint(condition=Q(net_weight__gte=0), name="inventory_tx_net_nonnegative")),
        migrations.AddConstraint(model_name="inventorytransaction", constraint=models.CheckConstraint(condition=Q(fine_weight__gte=0), name="inventory_tx_fine_nonnegative")),
        migrations.AddConstraint(model_name="inventorytransaction", constraint=models.CheckConstraint(condition=Q(value__gte=0), name="inventory_tx_value_nonnegative")),
    ]
