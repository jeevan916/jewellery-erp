from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import AccountGroup,Account,FinancialPeriod,Party,BillReference,VoucherType,Voucher
from .services.payments import create_payment,post_payment,allocate_payment,deallocate_payment,active_allocated

class PaymentEngineTests(TestCase):
    def setUp(self):
        g=AccountGroup.objects.create(code='1000',name='Assets',nature='ASSET')
        p=AccountGroup.objects.create(code='4000',name='Income',nature='INCOME')
        self.bank=Account.objects.create(code='1001',name='Bank',group=g,is_bank=True)
        self.customer_account=Account.objects.create(code='1100',name='Customer',group=g,is_party_account=True)
        self.customer=Party.objects.create(code='C1',name='Customer',party_type='CUSTOMER',account=self.customer_account)
        self.period=FinancialPeriod.objects.create(name='FY',starts_on=date(2026,4,1),ends_on=date(2027,3,31),status='OPEN')
        vt=VoucherType.objects.create(code='SALES',name='Sales',category='SALES',prefix='INV')
        v=Voucher.objects.create(voucher_type=vt,number='INV-1',voucher_date=date(2026,9,10),status='POSTED')
        self.bill=BillReference.objects.create(party=self.customer,voucher=v,bill_number='INV-1',bill_date=date(2026,9,10),bill_type='RECEIVABLE',amount=Decimal('1000'))
    def test_receipt_and_partial_allocation(self):
        p=create_payment(party_id=self.customer.id,payment_type='RECEIPT',voucher_number='R-1',payment_date=date(2026,9,10),amount=Decimal('600'),account_id=self.bank.id)
        post_payment(payment_id=p.id,financial_period_id=self.period.id,account_id=self.bank.id)
        allocate_payment(payment_id=p.id,bill_id=self.bill.id,amount=Decimal('400'))
        self.assertEqual(active_allocated(payment_id=p.id),Decimal('400.0000'))
        self.bill.refresh_from_db(); self.assertEqual(self.bill.outstanding_amount,Decimal('600.0000'))
    def test_overallocation_rejected(self):
        p=create_payment(party_id=self.customer.id,payment_type='RECEIPT',voucher_number='R-2',payment_date=date(2026,9,10),amount=Decimal('600'),account_id=self.bank.id)
        post_payment(payment_id=p.id,financial_period_id=self.period.id,account_id=self.bank.id)
        with self.assertRaises(ValidationError): allocate_payment(payment_id=p.id,bill_id=self.bill.id,amount=Decimal('700'))
    def test_deallocation_is_append_only(self):
        p=create_payment(party_id=self.customer.id,payment_type='RECEIPT',voucher_number='R-3',payment_date=date(2026,9,10),amount=Decimal('600'),account_id=self.bank.id)
        post_payment(payment_id=p.id,financial_period_id=self.period.id,account_id=self.bank.id)
        a=allocate_payment(payment_id=p.id,bill_id=self.bill.id,amount=Decimal('600'))
        deallocate_payment(allocation_id=a.id)
        self.assertEqual(a.__class__.objects.filter(payment=p).count(),2)
        self.assertEqual(active_allocated(payment_id=p.id),Decimal('0.0000'))
