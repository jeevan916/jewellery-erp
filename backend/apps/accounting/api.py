from datetime import date
from django.contrib.auth import authenticate
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status
from .models import Account, AccountGroup, BillReference, FinancialPeriod, JournalEntryLine, Party, Payment, PaymentAllocation, SalesInvoice
from .services.payments import create_payment, post_payment, allocate_payment, deallocate_payment, active_allocated
from .services.reports import trial_balance, profit_and_loss, balance_sheet
from .services.ledger import account_ledger, account_t_shape
from .services.sales import create_sales_invoice, post_sales_invoice

def dec(v): return str(v)

def account_row(a): return {'id':a.id,'code':a.code,'name':a.name,'group':a.group.name,'group_code':a.group.code,'is_cash':a.is_cash,'is_bank':a.is_bank,'is_clearing':a.is_clearing,'is_party_account':a.is_party_account}
def party_row(p): return {'id':p.id,'code':p.code,'name':p.name,'party_type':p.party_type,'account_id':p.account_id,'gstin':p.gstin,'phone':p.phone}

def invoice_row(x):
    bill=BillReference.objects.filter(voucher=x.voucher).first()
    return {'id':x.id,'invoice_number':x.invoice_number,'date':x.invoice_date,'customer_id':x.customer_id,'customer':x.customer.name,'taxable_value':dec(x.taxable_value),'cgst':dec(x.cgst),'sgst':dec(x.sgst),'igst':dec(x.igst),'total':dec(x.total_amount),'status':x.status,'outstanding':dec(bill.outstanding_amount if bill else x.total_amount)}

def payment_row(x): return {'id':x.id,'voucher_number':x.voucher.number,'date':x.payment_date,'party_id':x.party_id,'party':x.party.name,'type':x.payment_type,'amount':dec(x.amount),'allocated':dec(active_allocated(payment_id=x.id)),'unallocated':dec(x.amount-active_allocated(payment_id=x.id)),'status':x.status,'reference':x.reference}

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    u=authenticate(username=request.data.get('username',''),password=request.data.get('password',''))
    if not u: return Response({'detail':'Invalid username or password.'},status=400)
    token,_=Token.objects.get_or_create(user=u)
    return Response({'token':token.key,'user':{'id':u.id,'username':u.username,'is_staff':u.is_staff}})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    return Response({'customers':Party.objects.filter(party_type='CUSTOMER',is_active=True).count(),'suppliers':Party.objects.filter(party_type='SUPPLIER',is_active=True).count(),'invoices':SalesInvoice.objects.count(),'posted_invoices':SalesInvoice.objects.filter(status='POSTED').count(),'receipts':Payment.objects.filter(payment_type='RECEIPT',status='POSTED').count(),'open_bills':BillReference.objects.filter(status='OPEN').count(),'accounts':Account.objects.filter(is_active=True).count()})

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def parties(request):
    if request.method=='GET': return Response([party_row(x) for x in Party.objects.select_related('account').all()])
    d=request.data; account=Account.objects.get(pk=d['account_id'])
    p=Party.objects.create(code=d['code'],name=d['name'],party_type=d.get('party_type','CUSTOMER'),account=account,gstin=d.get('gstin',''),phone=d.get('phone',''))
    return Response(party_row(p),status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def accounts(request): return Response([account_row(x) for x in Account.objects.select_related('group').filter(is_active=True)])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def periods(request): return Response([{'id':x.id,'name':x.name,'starts_on':x.starts_on,'ends_on':x.ends_on,'status':x.status} for x in FinancialPeriod.objects.all()])

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def invoices(request):
    if request.method=='GET': return Response([invoice_row(x) for x in SalesInvoice.objects.select_related('customer').all()])
    d=request.data
    x=create_sales_invoice(customer_id=d['customer_id'],voucher_number=d.get('voucher_number',d['invoice_number']),invoice_number=d['invoice_number'],invoice_date=d.get('invoice_date',date.today()),due_date=d.get('due_date'),lines=d['lines'],cgst=d.get('cgst',0),sgst=d.get('sgst',0),igst=d.get('igst',0),narration=d.get('narration',''))
    return Response(invoice_row(x),status=201)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invoice_post(request,pk):
    d=request.data
    x,b,e=post_sales_invoice(invoice_id=pk,financial_period_id=d['financial_period_id'],receivable_account_id=d['receivable_account_id'],sales_account_id=d['sales_account_id'],cgst_account_id=d.get('cgst_account_id'),sgst_account_id=d.get('sgst_account_id'),igst_account_id=d.get('igst_account_id'))
    return Response(invoice_row(x))

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def payments(request):
    if request.method=='GET': return Response([payment_row(x) for x in Payment.objects.select_related('party','voucher').all()])
    d=request.data
    x=create_payment(party_id=d['party_id'],payment_type=d.get('payment_type','RECEIPT'),voucher_number=d['voucher_number'],payment_date=d.get('payment_date',date.today()),amount=d['amount'],account_id=d['account_id'],reference=d.get('reference',''),narration=d.get('narration',''))
    return Response(payment_row(x),status=201)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payment_post(request,pk):
    x,e=post_payment(payment_id=pk,financial_period_id=request.data['financial_period_id'],account_id=request.data['account_id'])
    return Response(payment_row(x))

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def allocations(request):
    if request.method=='POST':
        x=allocate_payment(payment_id=request.data['payment_id'],bill_id=request.data['bill_id'],amount=request.data['amount'])
        return Response({'id':x.id,'payment_id':x.payment_id,'bill_id':x.bill_id,'amount':dec(x.amount)},status=201)
    qs=PaymentAllocation.objects.select_related('payment','bill','bill__party').all()
    return Response([{'id':x.id,'type':x.entry_type,'payment_id':x.payment_id,'bill_id':x.bill_id,'party':x.bill.party.name,'amount':dec(x.amount)} for x in qs])

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def allocation_deallocate(request,pk):
    x=deallocate_payment(allocation_id=pk,amount=request.data.get('amount'))
    return Response({'id':x.id,'type':x.entry_type,'amount':dec(x.amount)})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def outstanding(request):
    rows=[]
    for b in BillReference.objects.select_related('party').filter(status='OPEN'):
        out=b.outstanding_amount
        if out: rows.append({'id':b.id,'bill_number':b.bill_number,'party':b.party.name,'party_id':b.party_id,'date':b.bill_date,'due_date':b.due_date,'type':b.bill_type,'amount':dec(b.amount),'outstanding':dec(out)})
    return Response(rows)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ledger(request,pk):
    return Response(account_ledger(pk,start_date=request.query_params.get('start_date'),end_date=request.query_params.get('end_date')))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report(request,name):
    if name=='trial-balance': r=trial_balance(start_date=request.query_params.get('start_date'),end_date=request.query_params.get('end_date'))
    elif name=='profit-loss': r=profit_and_loss(start_date=request.query_params.get('start_date'),end_date=request.query_params.get('end_date'))
    elif name=='balance-sheet': r=balance_sheet(as_of_date=request.query_params.get('as_of_date'))
    else: return Response({'detail':'Unknown report'},status=404)
    def clean(v):
        if isinstance(v,dict): return {k:clean(x) for k,x in v.items()}
        if isinstance(v,list): return [clean(x) for x in v]
        if hasattr(v,'as_tuple'): return dec(v)
        return v
    return Response(clean(r))
