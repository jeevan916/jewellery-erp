from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from apps.accounting.models import Account, BillReference, FinancialPeriod, Party, Payment, PaymentAllocation, Voucher, VoucherType
from apps.accounting.services.posting import post_voucher

ZERO=Decimal('0.0000')
def money(v): return Decimal(str(v)).quantize(Decimal('0.0001'))
def active_account(pk):
    a=Account.objects.filter(pk=pk,is_active=True).first()
    if not a: raise ValidationError('Account is missing or inactive.')
    return a

def create_payment(*,party_id,payment_type,voucher_number,payment_date,amount,account_id,reference='',narration=''):
    amount=money(amount)
    if amount<=ZERO: raise ValidationError('Payment amount must be positive.')
    party=Party.objects.get(pk=party_id)
    expected=Party.PartyType.CUSTOMER if payment_type==Payment.PaymentType.RECEIPT else Party.PartyType.SUPPLIER
    if party.party_type!=expected: raise ValidationError('Party type does not match payment type.')
    active_account(account_id)
    with transaction.atomic():
        code='RECEIPT' if payment_type==Payment.PaymentType.RECEIPT else 'PAYMENT'
        vt,_=VoucherType.objects.get_or_create(code=code,defaults={'name':code.title(),'category':code,'prefix':'RCPT' if code=='RECEIPT' else 'PAY'})
        voucher=Voucher.objects.create(voucher_type=vt,number=voucher_number,voucher_date=payment_date,status=Voucher.Status.DRAFT,reference=reference,narration=narration)
        return Payment.objects.create(party=party,voucher=voucher,payment_date=payment_date,payment_type=payment_type,amount=amount,reference=reference,narration=narration)

@transaction.atomic
def post_payment(*,payment_id,financial_period_id,account_id):
    p=Payment.objects.select_for_update().select_related('party').get(pk=payment_id)
    if p.status!=Payment.Status.DRAFT: raise ValidationError('Only a draft payment can be posted.')
    FinancialPeriod.objects.select_for_update().get(pk=financial_period_id)
    active_account(account_id); pa=active_account(p.party.account_id)
    if p.payment_type==Payment.PaymentType.RECEIPT:
        lines=[{'account_id':account_id,'debit':p.amount,'narration':p.reference or 'Receipt'},{'account_id':pa.id,'credit':p.amount,'narration':p.reference or 'Receipt'}]
    else:
        lines=[{'account_id':pa.id,'debit':p.amount,'narration':p.reference or 'Payment'},{'account_id':account_id,'credit':p.amount,'narration':p.reference or 'Payment'}]
    entry=post_voucher(voucher_id=p.voucher_id,lines=lines,period_id=financial_period_id)
    p.status=Payment.Status.POSTED; p.save(update_fields=['status'])
    return p,entry

def active_allocated(*,payment_id=None,bill_id=None):
    qs=PaymentAllocation.objects.filter(payment_id=payment_id) if payment_id else PaymentAllocation.objects.filter(bill_id=bill_id)
    a=qs.filter(entry_type=PaymentAllocation.EntryType.ALLOCATE).aggregate(v=Sum('amount'))['v'] or ZERO
    d=qs.filter(entry_type=PaymentAllocation.EntryType.DEALLOCATE).aggregate(v=Sum('amount'))['v'] or ZERO
    return max(a-d,ZERO)

@transaction.atomic
def allocate_payment(*,payment_id,bill_id,amount):
    amount=money(amount); p=Payment.objects.select_for_update().get(pk=payment_id); b=BillReference.objects.select_for_update().get(pk=bill_id)
    if p.status!=Payment.Status.POSTED: raise ValidationError('Only a posted payment can be allocated.')
    if p.party_id!=b.party_id: raise ValidationError('Payment and bill must belong to the same party.')
    expected=BillReference.BillType.RECEIVABLE if p.payment_type==Payment.PaymentType.RECEIPT else BillReference.BillType.PAYABLE
    if b.bill_type!=expected: raise ValidationError('Bill type does not match payment type.')
    ap=p.amount-active_allocated(payment_id=p.id); ab=b.amount-active_allocated(bill_id=b.id)
    if amount<=ZERO or amount>ap or amount>ab: raise ValidationError(f'Allocation exceeds available amount. Payment={ap}, Bill={ab}.')
    x=PaymentAllocation.objects.create(payment=p,bill=b,entry_type=PaymentAllocation.EntryType.ALLOCATE,amount=amount)
    BillReference.objects.filter(pk=b.pk).update(status=BillReference.Status.SETTLED if ab==amount else BillReference.Status.OPEN)
    return x

@transaction.atomic
def deallocate_payment(*,allocation_id,amount=None):
    a=PaymentAllocation.objects.select_for_update().get(pk=allocation_id)
    if a.entry_type!=PaymentAllocation.EntryType.ALLOCATE: raise ValidationError('Only an allocation can be deallocated.')
    released=PaymentAllocation.objects.filter(reference_allocation_id=a.id,entry_type=PaymentAllocation.EntryType.DEALLOCATE).aggregate(v=Sum('amount'))['v'] or ZERO
    remaining=a.amount-released; amount=remaining if amount is None else money(amount)
    if amount<=ZERO or amount>remaining: raise ValidationError('Invalid deallocation amount.')
    x=PaymentAllocation.objects.create(payment_id=a.payment_id,bill_id=a.bill_id,entry_type=PaymentAllocation.EntryType.DEALLOCATE,amount=amount,reference_allocation=a)
    BillReference.objects.filter(pk=a.bill_id).update(status=BillReference.Status.OPEN)
    return x
