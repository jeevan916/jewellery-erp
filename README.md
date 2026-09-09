# Jewellery ERP

Production-grade, offline-first jewellery ERP for Indian jewellery retail and operations.

## Architecture

- **Web/Admin/POS:** React + TypeScript + Vite
- **Desktop:** Electron
- **Backend:** Django + Django REST Framework
- **Cloud database:** PostgreSQL
- **Local database:** SQLite
- **Sync:** transactional outbox/inbox with retry, idempotency and conflict handling
- **Documents:** immutable original files + extraction/review pipeline
- **Accounting:** Tally-style double-entry accounting with journal-derived ledgers

## Core principles

1. Financial records are immutable. Corrections use reversal/reallocation workflows.
2. Every posted voucher produces balanced journal entries.
3. Ledgers and reports are projections of journal lines; they are never independently maintained balances.
4. Payment gateways such as Razorpay and Paytm are clearing accounts when settlement differs from gross receipts.
5. Imported statements are preserved in original form and linked to normalized transactions, reconciliation and vouchers.
6. OCR/document extraction is assistive only. Financial posting requires review/approval.
7. Offline billing must remain safe and synchronizable after connectivity returns.
8. Tenant, branch, user, role and audit boundaries are enforced server-side.

## Planned modules

- Accounting and Chart of Accounts
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
- Reports: Day Book, Ledger, Trial Balance, P&L, Balance Sheet, outstanding and reconciliation
- RBAC, approvals and immutable audit trail
- Offline-first desktop and cloud synchronization

## Development status

Phase 0 — architecture and domain foundation.
