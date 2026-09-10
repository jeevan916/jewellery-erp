# Jewellery ERP Backend

Django + Django REST Framework backend for the online-only Jewellery ERP.

## Stack

- Python 3.12+
- Django
- Django REST Framework
- MySQL / InnoDB

## Design rules

1. PostgreSQL is not used by this project.
2. SQLite is not used as an accounting fallback.
3. Financial posting is server-side only.
4. Money uses `Decimal` / fixed-precision database fields.
5. Posted financial records are immutable.
6. Financial writes use database transactions.
7. Business modules call accounting services; they do not duplicate ledger state.
8. All sensitive operations require server-side authorization.

## Planned Django apps

```text
apps/
  core/
  organizations/
  parties/
  accounting/
  sales/
  purchases/
  inventory/
  payments/
  reconciliation/
  documents/
  gst/
  audit/
```

The accounting app is the first domain implementation. Other modules should depend on its public services rather than manipulating journal tables directly.
