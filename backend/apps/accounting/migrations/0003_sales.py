from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [("accounting", "0002_billwise")]

    operations = [
        migrations.CreateModel(
            name="SalesInvoice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("invoice_number", models.CharField(max_length=80)),
                ("invoice_date", models.DateField()),
                ("due_date", models.DateField(blank=True, null=True)),
                ("taxable_value", models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19)),
                ("cgst", models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19)),
                ("sgst", models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19)),
                ("igst", models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19)),
                ("discount", models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19)),
                ("total_amount", models.DecimalField(decimal_places=4, max_digits=19)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("POSTED", "Posted"), ("REVERSED", "Reversed"), ("CANCELLED", "Cancelled")], default="DRAFT", max_length=10)),
                ("narration", models.CharField(blank=True, max_length=255)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sales_invoices", to="accounting.party")),
                ("voucher", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="sales_invoice", to="accounting.voucher")),
            ],
            options={"ordering": ["-invoice_date", "-id"], "indexes": [models.Index(fields=["invoice_date", "customer", "status"], name="sales_inv_date_customer_idx")]},
        ),
        migrations.CreateModel(
            name="SalesInvoiceLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("line_no", models.PositiveIntegerField()),
                ("description", models.CharField(max_length=255)),
                ("hsn_code", models.CharField(blank=True, max_length=20)),
                ("quantity", models.DecimalField(decimal_places=6, max_digits=19)),
                ("rate", models.DecimalField(decimal_places=4, max_digits=19)),
                ("discount", models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19)),
                ("taxable_value", models.DecimalField(decimal_places=4, max_digits=19)),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lines", to="accounting.salesinvoice")),
            ],
        ),
        migrations.AddConstraint(model_name="salesinvoice", constraint=models.UniqueConstraint(fields=["customer", "invoice_number"], name="uq_customer_sales_invoice")),
        migrations.AddConstraint(model_name="salesinvoice", constraint=models.CheckConstraint(condition=Q(total_amount__gt=0), name="sales_invoice_total_positive")),
        migrations.AddConstraint(model_name="salesinvoiceline", constraint=models.UniqueConstraint(fields=["invoice", "line_no"], name="uq_sales_invoice_line_no")),
        migrations.AddConstraint(model_name="salesinvoiceline", constraint=models.CheckConstraint(condition=Q(quantity__gt=0), name="sales_line_quantity_positive")),
        migrations.AddConstraint(model_name="salesinvoiceline", constraint=models.CheckConstraint(condition=Q(rate__gte=0), name="sales_line_rate_nonnegative")),
        migrations.AddConstraint(model_name="salesinvoiceline", constraint=models.CheckConstraint(condition=Q(taxable_value__gte=0), name="sales_line_taxable_nonnegative")),
    ]
