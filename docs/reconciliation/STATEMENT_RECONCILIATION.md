# Bank and POS Statement Reconciliation

## 1. Scope

The ERP must import and reconcile statements from:

- DBS Bank
- YES BANK
- Bank of Baroda
- Paytm POS
- Razorpay POS

Supported source formats:

- PDF
- XLSX/Excel
- CSV

The design must allow additional banks and payment providers without changing the accounting model.

## 2. Immutable source document

The original uploaded statement is preserved unchanged.

Statement metadata includes:

- source/provider
- account or merchant identifier
- statement period
- original filename
- file type
- file hash
- uploader
- upload timestamp
- processing status
- approval status

The original file must not be overwritten after upload.

## 3. Lifecycle

```text
Uploaded
   |
   v
Processing
   |
   v
Extracted
   |
   v
Needs Review
   |
   v
Approved
   |
   v
Voucher Created
   |
   v
Reconciled
```

Errors move to a review/error state with an actionable explanation rather than silently dropping rows.

## 4. Import pipeline

```text
Original PDF/XLSX/CSV
        |
        v
Parser / PDF extraction / OCR
        |
        v
Normalized transaction records
        |
        v
Validation + duplicate detection
        |
        v
Matching engine
        |
        v
Human review
        |
        v
Receipt / Payment / Journal
        |
        v
Reconciliation
```

Scanned PDFs may require OCR. OCR output is never treated as automatically correct.

## 5. Normalized transaction

A statement transaction should retain source information and normalized fields such as:

- transaction date
- value date when available
- debit/credit direction
- amount
- currency
- narration
- reference number
- UTR/RRN/gateway reference
- counterparty text
- source row/page
- source document
- import batch
- duplicate fingerprint
- reconciliation state
- linked voucher

Raw extracted values should remain available for review.

## 6. Duplicate detection

Duplicate detection operates at multiple levels:

### File level

Use a cryptographic hash of the original file.

### Transaction level

Use deterministic fingerprints based on available source identifiers, amount, date, direction and normalized reference/narration.

The system must distinguish a genuine duplicate import from two legitimate transactions with similar amounts.

Never delete an imported transaction merely because it looks duplicated. Mark it for review or retain the duplicate relationship.

## 7. Matching strategy

Matching should consider:

1. exact UTR/RRN/reference
2. gateway transaction ID
3. exact invoice/reference number
4. exact amount
5. transaction date and acceptable settlement window
6. customer/supplier identity
7. narration similarity
8. payment mode
9. outstanding invoice balance

The engine should return a confidence score and explanation, not just a yes/no result.

Example:

```text
₹118,000
Reference: ABC123
Date: 05-Apr

Candidate invoice: INV-1001
Amount: ₹118,000
Reference: ABC123
Customer: ABC Jewellers

Confidence: HIGH
Reasons: exact reference + exact amount + valid outstanding
```

## 8. Human confirmation

High-confidence matches can be suggested, but the system should preserve the approval/reconciliation action and actor.

Ambiguous transactions should enter a review queue.

The system must never silently post an uncertain transaction to a customer account.

## 9. One-to-many and many-to-one allocation

The matching model must support:

```text
One bank transaction
   -> Invoice A
   -> Invoice B
   -> Invoice C
```

and:

```text
Invoice A
   -> Payment 1
   -> Payment 2
   -> Payment 3
```

Partial payments and overpayments are first-class cases.

Overpayments become customer advances/credit balances according to accounting rules.

## 10. Suspense workflow

Unmatched receipts are parked safely:

```text
Imported receipt
      |
      +--> matched --> customer receipt --> allocation
      |
      +--> unmatched --> Suspense / Unallocated
                               |
                               v
                       manual identification
                               |
                               v
                         final allocation
```

Reclassification must retain the original transaction, original suspense state and subsequent accounting action.

## 11. Gateway settlement

Gateway imports should support gross collection and net settlement.

For example:

```text
Customer payment
      |
      v
Razorpay Clearing
      |
      +--> gateway fee
      +--> GST on fee
      |
      v
Bank settlement
```

The reconciliation dashboard should therefore reconcile the gateway clearing account, not merely count bank deposits.

## 12. Reconciliation sessions

A reconciliation session should record:

- source account/provider
- statement period
- opening/closing balance where available
- imported transaction count
- duplicate count
- matched count
- suggested count
- unmatched count
- suspense count
- manually changed count
- voucher-created count
- reconciled count
- reviewer
- approval timestamp

## 13. Auditability

For every manual change, preserve:

- user
- timestamp
- old value
- new value
- reason/comment where required
- source transaction
- affected voucher
- affected journal entry

Document view/download actions should also be auditable for sensitive financial documents.

## 14. CA/accountant access

CA/accountant access is separate from owner credentials.

Permissions should be granular, for example:

- view statements
- upload statements
- download originals
- review extraction
- approve imports
- suggest matches
- confirm reconciliation
- create vouchers
- edit reconciliation rules
- view accounting
- export reports

Authorization is enforced server-side.

## 15. Reconciliation dashboard

The UI should make exceptions obvious:

```text
DBS BANK
Imported: 1,248
Matched: 1,167
Suggested: 42
Unmatched: 31
Suspense: 8

[Review Exceptions]
```

Every count should drill down to the underlying transactions.

## 16. Source traceability

Every resulting voucher should be traceable back to:

```text
Voucher
  -> journal entry
  -> reconciliation match
  -> normalized statement transaction
  -> import batch
  -> original statement file
```

The reverse path must also work.
