# Jewellery ERP Backend

Django + Django REST Framework backend for the online-only Jewellery ERP.

## Stack
- Python 3.12+
- Django
- Django REST Framework
- MySQL / InnoDB

## Accounting foundation
Chart of accounts, financial periods, voucher types, vouchers, journal entries, journal lines, transactional posting, and invariant tests are implemented as the first backend domain.

Business modules must call accounting services and must not maintain a second ledger state.
