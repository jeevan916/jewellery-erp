from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounting.models import AccountGroup, Account, FinancialPeriod, Party

class Command(BaseCommand):
    help='Create local development user, accounts and sample parties.'
    def handle(self,*args,**kwargs):
        User=get_user_model(); u,created=User.objects.get_or_create(username='admin',defaults={'is_staff':True,'is_superuser':True}); u.is_staff=True; u.is_superuser=True; u.set_password('admin'); u.save()
        groups=[('1000','Assets','ASSET'),('2000','Liabilities','LIABILITY'),('3000','Equity','EQUITY'),('4000','Income','INCOME'),('5000','Expenses','EXPENSE')]
        gs={}
        for code,name,nature in groups: gs[code]=AccountGroup.objects.get_or_create(code=code,defaults={'name':name,'nature':nature,'is_system':True})[0]
        accounts=[('1001','Cash',gs['1000'],True,False,False,False),('1002','Bank',gs['1000'],False,True,False,False),('1100','Customer Control',gs['1000'],False,False,False,True),('4001','Sales',gs['4000'],False,False,False,False),('2201','CGST Output',gs['2000'],False,False,False,False),('2202','SGST Output',gs['2000'],False,False,False,False),('5001','Bank Charges',gs['5000'],False,False,False,False)]
        amap={}
        for code,name,g,cash,bank,clear,party in accounts: amap[code]=Account.objects.get_or_create(code=code,defaults={'name':name,'group':g,'is_cash':cash,'is_bank':bank,'is_clearing':clear,'is_party_account':party})[0]
        customers=[('C001','Demo Customer','999999999999999','9000000001')]
        for code,name,gstin,phone in customers: Party.objects.get_or_create(code=code,defaults={'name':name,'party_type':'CUSTOMER','account':amap['1100'],'gstin':gstin,'phone':phone})
        FinancialPeriod.objects.get_or_create(name='FY 2026-27',starts_on=date(2026,4,1),ends_on=date(2027,3,31),defaults={'status':'OPEN'})
        self.stdout.write(self.style.SUCCESS('Demo environment ready. Login: admin / admin'))
