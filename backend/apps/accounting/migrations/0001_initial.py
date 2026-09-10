from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="AccountGroup", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=120)), ("code", models.CharField(max_length=40)),
            ("nature", models.CharField(choices=[("ASSET", "Asset"), ("LIABILITY", "Liability"), ("EQUITY", "Equity"), ("INCOME", "Income"), ("EXPENSE", "Expense")], max_length=12)), ("is_system", models.BooleanField(default=False)), ("is_active", models.BooleanField(default=True)),
            ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="accounting.accountgroup")),
        ], options={"ordering": ["code"]}),
        migrations.CreateModel(name="FinancialPeriod", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=80)), ("starts_on", models.DateField()), ("ends_on", models.DateField()), ("status", models.CharField(choices=[("OPEN", "Open"), ("CLOSED", "Closed"), ("LOCKED", "Locked")], default="OPEN", max_length=10)),
        ]),
        migrations.CreateModel(name="VoucherType", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("code", models.CharField(max_length=30, unique=True)), ("name", models.CharField(max_length=100)), ("category", models.CharField(max_length=40)), ("prefix", models.CharField(blank=True, max_length=20)), ("is_system", models.BooleanField(default=False)), ("is_active", models.BooleanField(default=True)),
        ], options={"ordering": ["code"]}),
        migrations.CreateModel(name="Voucher", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("number", models.CharField(max_length=50)), ("voucher_date", models.DateField()), ("status", models.CharField(choices=[("DRAFT", "Draft"), ("POSTED", "Posted"), ("REVERSED", "Reversed"), ("CANCELLED", "Cancelled")], default="DRAFT", max_length=10)), ("reference", models.CharField(blank=True, max_length=120)), ("narration", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("posted_at", models.DateTimeField(blank=True, null=True)), ("reversal_of", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reversal", to="accounting.voucher")), ("voucher_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="vouchers", to="accounting.vouchertype")),
        ], options={"indexes": [models.Index(fields=["voucher_date", "status"], name="accounting_voucher_date_status_idx")]}),
        migrations.CreateModel(name="Account", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=160)), ("code", models.CharField(max_length=40)), ("account_type", models.CharField(choices=[("LEDGER", "Ledger"), ("CONTROL", "Control")], default="LEDGER", max_length=12)), ("is_party_account", models.BooleanField(default=False)), ("is_cash", models.BooleanField(default=False)), ("is_bank", models.BooleanField(default=False)), ("is_clearing", models.BooleanField(default=False)), ("is_system", models.BooleanField(default=False)), ("is_active", models.BooleanField(default=True)), ("group", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="accounts", to="accounting.accountgroup")),
        ], options={"ordering": ["code"]}),
        migrations.CreateModel(name="JournalEntry", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("entry_date", models.DateField()), ("status", models.CharField(choices=[("POSTED", "Posted"), ("REVERSED", "Reversed")], default="POSTED", max_length=10)), ("total_debit", models.DecimalField(decimal_places=4, default=0, max_digits=19)), ("total_credit", models.DecimalField(decimal_places=4, default=0, max_digits=19)), ("posted_at", models.DateTimeField(auto_now_add=True)), ("financial_period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="journal_entries", to="accounting.financialperiod")), ("voucher", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="journal_entry", to="accounting.voucher")),
        ], options={"indexes": [models.Index(fields=["entry_date", "status"], name="accounting_journal_entry_date_status_idx")]}),
        migrations.CreateModel(name="JournalEntryLine", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("line_no", models.PositiveIntegerField()), ("debit", models.DecimalField(decimal_places=4, default=0, max_digits=19)), ("credit", models.DecimalField(decimal_places=4, default=0, max_digits=19)), ("narration", models.CharField(blank=True, max_length=255)), ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="journal_lines", to="accounting.account")), ("journal_entry", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lines", to="accounting.journalentry")),
        ]),
        migrations.AddConstraint(model_name="accountgroup", constraint=models.UniqueConstraint(fields=["code"], name="uq_account_group_code")),
        migrations.AddConstraint(model_name="account", constraint=models.UniqueConstraint(fields=["code"], name="uq_account_code")),
        migrations.AddConstraint(model_name="account", constraint=models.CheckConstraint(condition=Q(is_cash=False) | Q(is_bank=False), name="account_not_both_cash_and_bank")),
        migrations.AddConstraint(model_name="financialperiod", constraint=models.UniqueConstraint(fields=["starts_on", "ends_on"], name="uq_financial_period_range")),
        migrations.AddConstraint(model_name="financialperiod", constraint=models.CheckConstraint(condition=Q(starts_on__lte=models.F("ends_on")), name="period_start_before_end")),
        migrations.AddConstraint(model_name="voucher", constraint=models.UniqueConstraint(fields=["voucher_type", "number"], name="uq_voucher_type_number")),
        migrations.AddConstraint(model_name="journalentryline", constraint=models.UniqueConstraint(fields=["journal_entry", "line_no"], name="uq_journal_line_no")),
        migrations.AddConstraint(model_name="journalentryline", constraint=models.CheckConstraint(condition=Q(debit__gte=0), name="journal_line_debit_nonnegative")),
        migrations.AddConstraint(model_name="journalentryline", constraint=models.CheckConstraint(condition=Q(credit__gte=0), name="journal_line_credit_nonnegative")),
        migrations.AddConstraint(model_name="journalentryline", constraint=models.CheckConstraint(condition=~(Q(debit__gt=0) & Q(credit__gt=0)), name="journal_line_not_both")),
        migrations.AddConstraint(model_name="journalentryline", constraint=models.CheckConstraint(condition=Q(debit__gt=0) | Q(credit__gt=0), name="journal_line_nonzero")),
    ]
