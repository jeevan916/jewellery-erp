from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounting", "0002_billwise")]

    operations = [
        migrations.AddField(
            model_name="paymentallocation",
            name="entry_type",
            field=models.CharField(
                choices=[("ALLOCATE", "Allocate"), ("DEALLOCATE", "Deallocate")],
                default="ALLOCATE",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="paymentallocation",
            name="reference_allocation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reversal_entries",
                to="accounting.paymentallocation",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="paymentallocation",
            name="uq_payment_bill_allocation",
        ),
        migrations.AddIndex(
            model_name="paymentallocation",
            index=models.Index(fields=["bill", "payment", "entry_type"], name="accounting_alloc_bill_payment_entry_idx"),
        ),
        migrations.AddIndex(
            model_name="paymentallocation",
            index=models.Index(fields=["payment", "bill", "allocated_at"], name="accounting_alloc_payment_bill_date_idx"),
        ),
    ]
