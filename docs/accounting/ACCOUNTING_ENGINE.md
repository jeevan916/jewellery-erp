# Accounting Engine

## 1. Objective

The accounting engine provides Tally-style double-entry accounting for jewellery retail while keeping financial history auditable and immutable.

The central rule is:

```text
Business transaction
       |
       v
     Voucher
       |
       v
  Accounting rules
       |
       v
 Journal Entry
       |
       v
 Journal Lines
       |
       +--> Ledgers
       +--> Outstanding
       +--> Trial Balance
       +--> P&L
       +--> Balance Sheet
```

Ledgers are derived from journal lines. They are never maintained as an independent financial truth.

## 2. Core entities

Minimum accounting entities:

- `account_groups`
- `accounts`
- `voucher_types`
- `voucher_number_sequences`
- `vouchers`
- `journal_entries`
- `journal_entry_lines`
- `bill_references`
- `payment_allocations`
- `financial_periods`
- `audit_logs`

Business modules such as sales, purchases and inventory reference accounting transactions but do not duplicate the ledger as a second source of truth.

## 3. Account hierarchy

Use a hierarchical Chart of Accounts similar to Tally:

```text
Assets
  Current Assets
    Cash
    Bank Accounts
    Payment Gateway Clearing
    Customer Receivables
    Inventory

Liabilities
  Current Liabilities
    Supplier Payables
    GST Payable
    Customer Advances

Income
  Sales
  Other Income

Expenses
  Purchase-related expenses
  Operating Expenses
  Bank Charges
  Payment Gateway Charges

Equity
  Capital
  Retained Earnings
```

Individual bank accounts, cash locations, gateways and parties should be represented as appropriate ledger accounts under their account groups.

## 4. Journal invariants

Every posted journal entry must satisfy:

```text
SUM(debit) = SUM(credit)
```

Additional invariants:

- at least one debit and one credit line
- valid account and tenant/branch scope
- valid financial period
- server-generated posting timestamp
- immutable posted state
- source voucher reference
- unique idempotency constraint where applicable

Never accept a client-provided final balance as authoritative.

## 5. Voucher types

The initial voucher catalog includes:

- Sales
- Purchase
- Receipt
- Payment
- Contra
- Journal
- Credit Note
- Debit Note
- Old Gold Purchase
- Old Gold Exchange
- Stock Journal
- Stock Transfer

Each voucher type defines validation and posting rules.

## 6. Sales example

For a taxable jewellery sale of ₹100,000 plus CGST ₹9,000 and SGST ₹9,000:

```text
Customer A/c              Dr 118,000
    To Sales A/c               100,000
    To Output CGST A/c           9,000
    To Output SGST A/c           9,000
```

The customer balance increases by ₹118,000.

A later receipt is a separate accounting event:

```text
Cash / Bank / Clearing A/c Dr 118,000
    To Customer A/c             118,000
```

## 7. Bill-wise accounting

Invoices and payments must support explicit bill references.

Required relationships:

```text
Invoice 1  ──┐
Invoice 2  ──┼──> Payment Allocation
Invoice 3  ──┘
```

A payment may be allocated across multiple invoices.

An invoice may receive multiple payments.

Partial payment is valid.

If a receipt exceeds all selected outstanding bills, the excess becomes a customer advance/credit balance rather than disappearing into an unexplained ledger balance.

## 8. Unallocated and suspense receipts

An imported bank/POS transaction must never be guessed into a customer account merely because the amount happens to match.

Uncertain receipts can be parked in Suspense/Unallocated Receipts and subsequently reclassified through an auditable workflow.

```text
Bank transaction
      |
      +--> confident match --> Receipt --> allocation
      |
      +--> uncertain -------> Suspense
                                  |
                                  v
                         human classification
                                  |
                                  v
                              Receipt
```

## 9. Payment gateway clearing

Payment gateways are clearing accounts when settlement differs from gross receipts.

Example: customer pays ₹100,000 through Razorpay; ₹1,000 gateway fee and ₹180 GST are deducted, and ₹98,820 reaches the bank.

Customer receipt:

```text
Razorpay Clearing A/c     Dr 100,000
    To Customer A/c           100,000
```

Settlement:

```text
Bank A/c                  Dr 98,820
Razorpay Charges A/c      Dr  1,000
Input GST A/c             Dr    180
    To Razorpay Clearing A/c 100,000
```

This allows the clearing ledger to be reconciled against the gateway statement.

The same pattern applies to Paytm POS and future gateways.

## 10. Tally-style ledger views

The UI should provide both:

### Running balance

```text
Date       Voucher       Debit      Credit      Balance
01-Apr     Opening       0          0           50,000 Dr
03-Apr     INV-1001      118,000    0           168,000 Dr
05-Apr     REC-0501      0          100,000      68,000 Dr
```

### T-shape ledger

```text
                 CUSTOMER A/C
------------------------------------------------
Debit                         | Credit
Date   Particulars  Amount    | Date  Particulars Amount
03-Apr INV-1001     118,000   | 05-Apr REC-0501   100,000
                              |
                              |
```

Every line must be drillable to the source voucher and business document.

## 11. Drill-down requirements

The user must be able to navigate in both directions:

```text
Ledger
  -> Journal line
  -> Journal entry
  -> Voucher
  -> Customer/Supplier
  -> Invoice
  -> Payment
  -> Bank/POS transaction
```

And:

```text
Bank/POS transaction
  -> Reconciliation match
  -> Voucher
  -> Journal entry
  -> Ledger
  -> Customer
  -> Invoice
```

## 12. Corrections

Posted financial history must not be overwritten.

Examples:

- wrong customer: reverse and post the correct allocation
- wrong invoice allocation: unallocate and reallocate
- wrong sale: use credit/debit note or reversal workflow
- wrong expense classification: correction journal with audit trail

The system should preserve who made the correction, when, why, and which original entry it affects.

## 13. Atomic posting

Posting should occur in a single database transaction:

```text
BEGIN
  validate voucher
  validate accounts
  lock affected records where required
  generate journal entry
  generate balanced journal lines
  create bill references / allocations
  update required projections
  write audit event
COMMIT
```

Any failure rolls back the entire operation.

## 14. Idempotency

Financial POST endpoints must support idempotency keys so that network retries cannot create duplicate receipts, sales or settlements.

The server must persist the idempotency result and return the same business result for a repeated request with the same valid key.

## 15. Period controls

Financial periods should support:

- open
- closed
- locked

Posting into a closed/locked period requires explicit authorized workflow rather than silently changing historical data.

## 16. Reporting

All accounting reports derive from posted journal lines:

- Day Book
- Ledger
- Group Summary
- Trial Balance
- Profit & Loss
- Balance Sheet
- Receivables
- Payables
- Bill-wise Outstanding
- Customer Advances
- Bank/Gateway Clearing
- Suspense/Unallocated Receipts

## 17. Non-negotiable rule

**No module is allowed to maintain a second independent version of the accounting truth.**

Sales, purchase, payment, old-gold and expense modules create business documents and invoke the accounting engine. The accounting engine creates the journal. Reports and ledgers read the resulting journal data.
