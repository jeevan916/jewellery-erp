# System Architecture

## 1. Architecture decision

Jewellery ERP is an **online-only, server-authoritative web application**.

Users access the application through a browser over HTTPS. There is no local accounting database, offline billing mode, Electron shell, or client/cloud synchronization layer.

```text
Desktop / Laptop / Tablet / Mobile
                |
              HTTPS
                v
        React + TypeScript
             Frontend
                |
             REST API
                v
        Django + DRF Backend
                |
       +--------+--------+
       |        |        |
 Accounting  Inventory  GST/Business
   Engine      Engine      Logic
       |        |        |
       +--------+--------+
                |
                v
           PostgreSQL
      Authoritative truth
                |
       +--------+--------+
       |        |        |
   Documents  Reports  Backups
```

## 2. Responsibilities

### React frontend

The frontend is responsible for:

- POS and administrative user interface
- forms and client-side validation for usability
- ledger and report presentation
- document upload/camera capture
- reconciliation workbench
- drill-down navigation
- displaying server-calculated balances and statuses

The frontend is **not** trusted for:

- accounting calculations
- authorization decisions
- voucher posting
- inventory valuation
- GST/tax determination
- financial balances
- audit history

### Django + DRF backend

The backend owns:

- authentication and authorization
- tenant/branch isolation
- business rules
- accounting engine
- inventory engine
- GST logic
- bill-wise allocation
- reconciliation
- document processing orchestration
- audit logging
- API validation
- transaction boundaries

### PostgreSQL

PostgreSQL is the single authoritative source of truth.

Financial writes must use database transactions and appropriate locking/idempotency controls. No business-critical financial state may exist only in browser storage.

## 3. Financial transaction boundary

Every financial business operation follows:

```text
User action
    |
    v
Validated API request
    |
    v
Business transaction / voucher
    |
    v
Accounting engine
    |
    v
Balanced journal entry
    |
    v
Journal lines
    |
    +----> Customer/Supplier outstanding
    +----> Ledger views
    +----> Trial Balance
    +----> P&L / Balance Sheet
    +----> Reconciliation links
    +----> Audit trail
```

Posting must be atomic: either the complete valid financial transaction is committed, or none of it is.

## 4. Immutable financial history

Posted accounting records are not edited destructively.

Corrections use explicit business operations such as:

- reversal
- credit/debit note
- unallocation
- reallocation
- adjustment journal
- correction voucher

The original transaction remains traceable.

## 5. API boundaries

The API should expose business resources rather than direct database CRUD for sensitive financial objects.

Examples:

```text
POST /api/v1/sales/{id}/post/
POST /api/v1/payments/{id}/allocate/
POST /api/v1/vouchers/{id}/reverse/
POST /api/v1/statements/{id}/approve/
POST /api/v1/reconciliation/matches/
POST /api/v1/documents/{id}/approve/
```

A generic endpoint must never allow a client to manufacture arbitrary journal lines without server-side validation.

## 6. Concurrency and idempotency

Online-only does not remove concurrency problems. Two users may post against the same customer, invoice, stock lot or cash account simultaneously.

Required controls include:

- database transactions
- row-level locking where needed
- unique constraints
- idempotency keys for retryable financial APIs
- server-generated voucher numbers
- server timestamps
- optimistic locking/version fields where useful
- validation immediately before commit

## 7. Documents

Uploaded invoices/statements are retained as immutable originals.

```text
Upload
  |
  v
Document Inbox
  |
  v
Extraction / OCR
  |
  v
Human Review
  |
  v
Approval
  |
  v
Business Voucher
  |
  v
Accounting / Inventory / GST
```

OCR output is never treated as authoritative without review/approval.

## 8. Statement reconciliation

Bank and POS imports follow:

```text
Original statement
       |
       v
Import batch
       |
       v
Normalized transactions
       |
       v
Duplicate detection
       |
       v
Match suggestions
       |
       v
Human confirmation
       |
       v
Receipt / payment / journal
       |
       v
Reconciled transaction
```

The original statement and normalized transaction remain linked to the resulting voucher and accounting entries.

## 9. Security model

Minimum controls:

- HTTPS everywhere
- secure session/token handling
- strong password policy and optional MFA
- server-side permission checks
- branch-level data isolation
- least-privilege CA/accountant access
- immutable audit logs
- download/view audit for sensitive documents
- protected document storage
- rate limiting for authentication and sensitive APIs
- CSRF protection where applicable
- strict input validation
- secure HTTP headers
- secrets outside source control
- automated backups

## 10. Production deployment

Target deployment is Hostinger. The deployment must keep application, database credentials and document storage protected from public access.

```text
Internet
   |
 HTTPS
   v
Reverse Proxy / Web Server
   |
   +---- React static assets
   |
   +---- Django application
             |
             +---- PostgreSQL
             +---- Redis/worker (when enabled)
             +---- Private document storage
```

Production deployment should have separate staging and production configuration, environment variables, logging, health checks and tested backups.

## 11. Explicit non-goals

This project does not implement:

- offline-first accounting
- local SQLite accounting
- Electron desktop packaging
- offline invoice queues
- client/server sync protocols
- conflict resolution between local and cloud databases
- browser-authoritative financial balances
