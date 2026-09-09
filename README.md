# Jewellery ERP

Production-grade, online-only jewellery ERP for Indian jewellery retail and operations.

## Architecture

- **Web/Admin/POS:** React + TypeScript + Vite
- **Backend/API:** Django + Django REST Framework
- **Database:** PostgreSQL — authoritative single source of truth
- **Deployment:** Hostinger production environment behind HTTPS/reverse proxy
- **Documents:** immutable original files + extraction/review pipeline
- **Accounting:** Tally-style double-entry accounting with journal-derived ledgers
- **Background jobs:** Redis/worker infrastructure when required for OCR, parsing, imports and reports

## Online-only principle

The application is intentionally **not offline-first**. Users operate against the hosted application and PostgreSQL database over HTTPS.

The browser is never treated as an accounting source of truth. All validation, authorization, accounting calculations, inventory movements, GST logic, voucher posting and financial integrity checks are enforced server-side.

### Explicitly excluded

- SQLite/local accounting database
- Electron desktop application
- Offline billing mode
- Local sync queues/outbox/inbox synchronization
- Conflict-resolution synchronization logic
- Local/cloud database reconciliation

## Core principles

1. PostgreSQL is the authoritative source of truth.
2. Financial records are immutable. Corrections use reversal, unallocation and reallocation workflows rather than destructive edits/deletes.
3. Every posted voucher produces balanced journal entries inside an atomic database transaction.
4. Ledgers and reports are projections of journal lines; they are never independently maintained balances.
5. Payment gateways such as Razorpay and Paytm are modeled as clearing accounts when settlement differs from gross customer receipts.
6. Imported statements are preserved in original form and linked to normalized transactions, reconciliation records and vouchers.
7. OCR/document extraction is assistive only. Financial posting requires human review/approval.
8. Bill-wise accounting supports partial payments, multi-invoice allocation, customer advances and unapplied/suspense receipts.
9. Tenant, branch, user, role, permission and audit boundaries are enforced server-side.
10. Original financial history and source documents remain traceable through every correction and reconciliation step.

## Planned modules

- Accounting and Chart of Accounts
- Tally-style vouchers and ledgers
- Sales/POS and GST billing
- Purchases and Registered Dealer (RD) purchases
- Inventory, HUID, purity and metal lots
- Old-gold purchase/exchange
- Customers, suppliers and bill-wise outstanding
- Cash, bank and payment gateway clearing
- Bank/POS statement import and reconciliation
- Expense capture from PDF/image/mobile camera
- Document Inbox and secure CA/accountant access
- Karigar/job work
- GST and tax ledgers
- Reports: Day Book, Ledger, Group Summary, Trial Balance, P&L, Balance Sheet, outstanding and reconciliation
- RBAC, approvals and immutable audit trail
- Automated backups and production monitoring

## Delivery phases

0. Architecture and domain foundation
1. Database and accounting primitives
2. Authentication, RBAC and tenancy/branch boundaries
3. Jewellery inventory engine
4. Billing and sales engine
5. Old-gold purchase/exchange engine
6. Payments, ledgers and GST
7. Bank/POS statements and reconciliation
8. Document Inbox, OCR, RD purchases and expense capture
9. React POS/Admin application
10. Reports and management dashboard
11. Security, integrity and failure testing
12. Hostinger staging and production deployment

## Development status

**Phase 0 — architecture and domain foundation.**

The repository is being built incrementally. Accounting integrity and server-side financial controls take priority over UI polish.
