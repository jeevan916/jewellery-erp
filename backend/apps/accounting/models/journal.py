from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from .core import Account, FinancialPeriod

class VoucherType(models.Model):
    code=models.CharField(max_length=30,unique=True); name=models.CharField(max_length=100); category=models.CharField(max_length=40); prefix=models.CharField(max_length=20,blank=True); is_system=models.BooleanField(default=False); is_active=models.BooleanField(default=True)
    class Meta: ordering=["code"]
    def __str__(self): return f"{self.code} - {self.name}"

class Voucher(models.Model):
    class Status(models.TextChoices): DRAFT="DRAFT","Draft"; POSTED="POSTED","Posted"; REVERSED="REVERSED","Reversed"; CANCELLED="CANCELLED","Cancelled"
    voucher_type=models.ForeignKey(VoucherType,on_delete=models.PROTECT,related_name="vouchers"); number=models.CharField(max_length=50); voucher_date=models.DateField(); status=models.CharField(max_length=10,choices=Status.choices,default=Status.DRAFT); reference=models.CharField(max_length=120,blank=True); narration=models.TextField(blank=True); reversal_of=models.OneToOneField("self",null=True,blank=True,on_delete=models.PROTECT,related_name="reversal"); created_at=models.DateTimeField(auto_now_add=True); posted_at=models.DateTimeField(null=True,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["voucher_type","number"],name="uq_voucher_type_number")]
        indexes=[models.Index(fields=["voucher_date","status"])]
    def __str__(self): return f"{self.voucher_type.code}-{self.number}"

class JournalEntry(models.Model):
    class Status(models.TextChoices): POSTED="POSTED","Posted"; REVERSED="REVERSED","Reversed"
    voucher=models.OneToOneField(Voucher,on_delete=models.PROTECT,related_name="journal_entry"); financial_period=models.ForeignKey(FinancialPeriod,on_delete=models.PROTECT,related_name="journal_entries"); entry_date=models.DateField(); status=models.CharField(max_length=10,choices=Status.choices,default=Status.POSTED); total_debit=models.DecimalField(max_digits=19,decimal_places=4,default=Decimal("0.0000")); total_credit=models.DecimalField(max_digits=19,decimal_places=4,default=Decimal("0.0000")); posted_at=models.DateTimeField(auto_now_add=True)
    class Meta: indexes=[models.Index(fields=["entry_date","status"])]
    def clean(self):
        if self.total_debit != self.total_credit: raise ValidationError("Journal entry debit and credit totals must balance.")

class JournalEntryLine(models.Model):
    journal_entry=models.ForeignKey(JournalEntry,on_delete=models.PROTECT,related_name="lines"); account=models.ForeignKey(Account,on_delete=models.PROTECT,related_name="journal_lines"); line_no=models.PositiveIntegerField(); debit=models.DecimalField(max_digits=19,decimal_places=4,default=Decimal("0.0000")); credit=models.DecimalField(max_digits=19,decimal_places=4,default=Decimal("0.0000")); narration=models.CharField(max_length=255,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["journal_entry","line_no"],name="uq_journal_line_no"),models.CheckConstraint(condition=Q(debit__gte=0),name="journal_line_debit_nonnegative"),models.CheckConstraint(condition=Q(credit__gte=0),name="journal_line_credit_nonnegative"),models.CheckConstraint(condition=~(Q(debit__gt=0)&Q(credit__gt=0)),name="journal_line_not_both"),models.CheckConstraint(condition=Q(debit__gt=0)|Q(credit__gt=0),name="journal_line_nonzero")]
    def clean(self):
        if self.debit and self.credit: raise ValidationError("A journal line cannot contain both debit and credit.")
        if self.debit == 0 and self.credit == 0: raise ValidationError("A journal line must have a debit or credit amount.")
