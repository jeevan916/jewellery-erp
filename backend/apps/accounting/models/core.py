from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class AccountGroup(models.Model):
    class Nature(models.TextChoices):
        ASSET = "ASSET", "Asset"
        LIABILITY = "LIABILITY", "Liability"
        EQUITY = "EQUITY", "Equity"
        INCOME = "INCOME", "Income"
        EXPENSE = "EXPENSE", "Expense"

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    nature = models.CharField(max_length=12, choices=Nature.choices)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["code"], name="uq_account_group_code")]
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Account(models.Model):
    class AccountType(models.TextChoices):
        LEDGER = "LEDGER", "Ledger"
        CONTROL = "CONTROL", "Control"

    group = models.ForeignKey(AccountGroup, on_delete=models.PROTECT, related_name="accounts")
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=40)
    account_type = models.CharField(max_length=12, choices=AccountType.choices, default=AccountType.LEDGER)
    is_party_account = models.BooleanField(default=False)
    is_cash = models.BooleanField(default=False)
    is_bank = models.BooleanField(default=False)
    is_clearing = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["code"], name="uq_account_code"),
            models.CheckConstraint(condition=Q(is_cash=False) | Q(is_bank=False), name="account_not_both_cash_and_bank"),
        ]
        ordering = ["code"]

    def clean(self):
        if self.is_cash and self.is_bank:
            raise ValidationError("An account cannot be both cash and bank.")

    def __str__(self):
        return f"{self.code} - {self.name}"


class FinancialPeriod(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"
        LOCKED = "LOCKED", "Locked"

    name = models.CharField(max_length=80)
    starts_on = models.DateField()
    ends_on = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["starts_on", "ends_on"], name="uq_financial_period_range"),
            models.CheckConstraint(condition=Q(starts_on__lte=models.F("ends_on")), name="period_start_before_end"),
        ]

    def __str__(self):
        return self.name
