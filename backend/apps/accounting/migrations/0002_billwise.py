from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("accounting", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Party",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("party_type", models.CharField(choices=[("CUSTOMER", "Customer"), ("SUPPLIER", "Supplier")], max_length=10)),
                ("gstin", models.CharField(blank=True, max_length=15)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("is_active", models.BooleanField(default=True)),
                ("account", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="party", to="accounting.account")),
            ],
            options={"ordering": ["code"], "indexes": [models.Index(fields=["party_type", "is_active"], name="accounting_party_type_active_idx")]},
        ),
        migrations.CreateModel(
            name="BillReference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bill_number", models.CharField(max_length=80)),
                ("bill_date", models.DateField()),
                ("due_date", models.DateField(blank=True, null=True)),
                ("bill_type", models.CharField(choices=[("RECEIVABLE", "Receivable"), ("PAYABLE", "Payable")], max_length=12)),
                ("amount", models.DecimalField(decimal_places=4, max_digits=19)),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("SETTLED", "Settled"), ("CANCELLED", "Cancelled")], default="OPEN", max_length=10)),
                ("narration", models.CharField(blank=True, max_length=255)),
                ("party", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bills", to="accounting.party")),
                ("voucher", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="bill_reference", to="accounting.voucher")),
            ],
            options={
                "ordering": ["bill_date", "id"],
                "indexes": [
                    models.Index(fields=["party", "status", "bill_date"], name="accounting_bill_party_status_date_idx"),
                    models.Index(fields=["due_date", "status"], name="accounting_bill_due_status_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payment_date", models.DateField()),
                ("payment_type", models.CharField(choices=[("RECEIPT", "Receipt"), ("PAYMENT", "Payment")], max_length=10)),
                ("amount", models.DecimalField(decimal_places=4, max_digits=19)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("POSTED", "Posted"), ("REVERSED", "Reversed")], default="DRAFT", max_length=10)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("narration", models.CharField(blank=True, max_length=255)),
                ("party", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="accounting.party")),
                ("voucher", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="payment", to="accounting.voucher")),
            ],
            options={"ordering": ["payment_date", "id"], "indexes": [models.Index(fields=["party", "payment_date", "status"], name="accounting_payment_party_date_status_idx")]},
        ),
        migrations.CreateModel(
            name="PaymentAllocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=4, max_digits=19)),
                ("allocated_at", models.DateTimeField(auto_now_add=True)),
                ("bill", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="allocations", to="accounting.billreference")),
                ("payment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="allocations", to="accounting.payment")),
            ],
            options={"indexes": [models.Index(fields=["bill", "payment"], name="accounting_alloc_bill_payment_idx")]},
        ),
        migrations.AddConstraint(model_name="billreference", constraint=models.UniqueConstraint(fields=["party", "bill_number"], name="uq_party_bill_number")),
        migrations.AddConstraint(model_name="billreference", constraint=models.CheckConstraint(condition=Q(amount__gt=0), name="bill_amount_positive")),
        migrations.AddConstraint(model_name="payment", constraint=models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive")),
        migrations.AddConstraint(model_name="paymentallocation", constraint=models.UniqueConstraint(fields=["payment", "bill"], name="uq_payment_bill_allocation")),
        migrations.AddConstraint(model_name="paymentallocation", constraint=models.CheckConstraint(condition=Q(amount__gt=0), name="allocation_amount_positive")),
    ]
