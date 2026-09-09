# Database Design — MySQL / InnoDB

## 1. Database decision

The application uses **MySQL with InnoDB** as the primary relational database.

The design remains deployment-agnostic: local development can use a local MySQL instance, while production can use Hostinger MySQL later. Database credentials are supplied through environment variables and are never committed to Git.

## 2. Design principles

- InnoDB for transactional integrity
- foreign keys for relational integrity
- decimal types for money and quantities where exact arithmetic is required
- UTC timestamps at the application/database boundary, with business timezone handling in the application
- explicit tenant/branch ownership on business data where applicable
- indexes designed around real query paths
- unique constraints for business identifiers and idempotency
- soft archive rather than destructive deletion for documents and appropriate master records
- posted financial records remain immutable

## 3. Initial domain model

### Organization

```text
organizations
branches
users
roles
permissions
user_roles
role_permissions
```

### Accounting

```text
account_groups
accounts
voucher_types
voucher_number_sequences
vouchers
journal_entries
journal_entry_lines
bill_references
payment_allocations
financial_periods
```

### Parties

```text
customers
suppliers
customer_accounts
supplier_accounts
```

### Sales and purchases

```text
sales
sale_items
purchases
purchase_items
payments
payment_methods
```

### Inventory

```text
items
item_categories
metal_types
purities
stock_lots
inventory_transactions
stock_transfers
stock_journals
```

### Reconciliation

```text
statements
statement_import_batches
statement_transactions
reconciliation_matches
reconciliation_sessions
reconciliation_rules
suspense_items
```

### Documents

```text
documents
document_extractions
document_review_events
ocr_jobs
```

### Controls

```text
approval_workflows
approval_actions
audit_logs
idempotency_keys
```

## 4. Money and quantity types

Money must use fixed-precision `DECIMAL`, not floating point.

Example:

```sql
DECIMAL(19,4)
```

This provides room for large values while retaining sub-rupee precision where required internally.

Weight and quantity fields should also use appropriate fixed precision, for example:

```sql
DECIMAL(19,6)
```

The exact scale will be standardized per domain field during implementation.

## 5. Accounting journal structure

A journal entry has a header and multiple lines:

```text
journal_entries
    |
    +-- journal_entry_lines
             |
             +-- account
             +-- debit
             +-- credit
             +-- party/bill reference where applicable
```

The database should enforce basic structural constraints, while the application service enforces the complete accounting invariant:

```text
SUM(debit) = SUM(credit)
```

## 6. Party and bill-wise accounting

Customer and supplier ledgers are accounting accounts linked to party masters.

Invoice-level references are represented separately so that:

- one invoice can have many payments
- one payment can allocate to many invoices
- partial allocation is supported
- customer advances can remain unallocated
- allocations can be reversed without deleting the original payment

## 7. Inventory and accounting separation

Inventory movements and accounting postings are related but distinct concepts.

```text
Stock movement
      |
      +--> inventory transaction
      |
      +--> valuation/accounting event when applicable
```

A stock quantity must not be treated as an accounting balance, and an accounting balance must not be inferred from a UI stock counter.

## 8. Statement import structure

The original file belongs to a statement/import batch.

```text
statement
   |
   +-- import_batch
          |
          +-- statement_transactions
                    |
                    +-- reconciliation_matches
                    +-- voucher links
```

Source metadata and raw extracted fields should remain available for audit/review.

## 9. Documents

Documents are metadata records pointing to private object/file storage. The database should store:

- document ID
- document type
- original filename
- MIME type
- size
- cryptographic hash
- storage key/path
- uploader
- created timestamp
- status
- source business object

The binary file itself should not be stored in ordinary accounting tables.

## 10. Idempotency

Financial API requests should carry an idempotency key.

Conceptually:

```text
(idempotency_key, user/tenant scope, endpoint scope) UNIQUE
```

A repeated request must return the original result instead of creating another financial transaction.

## 11. Indexing priorities

Initial indexes should cover:

- tenant/branch + transaction date
- account + journal date
- voucher number/type/date
- customer + outstanding state
- supplier + outstanding state
- invoice number/reference
- statement + transaction date
- statement reference/UTR
- reconciliation status
- document status
- audit actor + timestamp

Indexes will be refined after real query patterns are implemented and tested.

## 12. Financial integrity

Application services must use explicit database transactions around posting operations.

Where concurrent operations can affect the same financial resource, use appropriate row locks and re-check the invariant before commit.

Example:

```text
BEGIN
  lock invoice/customer rows as required
  validate outstanding amount
  create allocation
  create accounting journal
  validate balanced journal
COMMIT
```

## 13. Schema migration policy

All schema changes must be represented as versioned Django migrations.

Never modify production tables manually as part of normal application development.

Production migration procedures must include:

- backup/restore readiness
- migration ordering
- compatibility review
- rollback/recovery plan where feasible
- post-migration integrity checks

## 14. No browser database

The browser may cache UI data for performance, but it must never become a second accounting database.

The authoritative sequence is always:

```text
React request
   -> Django validation
   -> MySQL transaction
   -> committed truth
   -> API response
   -> React display
```
