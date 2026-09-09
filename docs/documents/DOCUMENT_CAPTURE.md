# Document Capture, OCR, RD Purchases and Expenses

## 1. Purpose

The ERP accepts financial documents from desktop and mobile browsers and turns them into reviewable business records.

Supported inputs:

- PDF
- image files
- mobile camera captures
- Excel/CSV where appropriate for statements

The original document is retained unchanged.

## 2. Document Inbox

All captured documents enter a central review queue:

```text
DOCUMENT INBOX

Pending Review: 17

[Invoice] ABC Bullion          Needs Review
[Bill] Electricity Board      Needs Review
[Receipt] Courier             Needs Review
[Statement] DBS Bank          Processing
```

The inbox prevents extracted data from bypassing human review.

## 3. Processing lifecycle

```text
Camera / PDF / Image
        |
        v
Secure upload
        |
        v
Document Inbox
        |
        v
Text extraction / OCR
        |
        v
Structured extraction
        |
        v
Human review
        |
        v
Approval
        |
        v
Business voucher
        |
        +--> Accounting
        +--> Inventory
        +--> GST
```

## 4. OCR rule

OCR and document understanding are **assistive only**.

They may suggest:

- vendor
- GSTIN
- invoice number
- invoice date
- HSN/SAC
- item description
- gross/net/fine weight
- purity
- rate
- making charges
- wastage
- discount
- taxable value
- CGST/SGST/IGST
- TCS
- total
- payment terms/mode

They must not independently create final posted financial entries without the required review/approval workflow.

## 5. Registered Dealer purchase

RD purchase records should support:

- supplier master
- supplier GSTIN
- invoice number/date
- material/category
- gold/silver/platinum
- jewellery
- gross weight
- net weight
- fine weight
- purity
- rate
- making charges
- wastage
- discount
- taxable value
- CGST/SGST/IGST
- TCS when applicable
- other charges
- freight/related costs
- total invoice value
- payment/credit terms
- bill-wise outstanding
- original document attachment

The exact tax/accounting treatment must be determined by configured business rules and reviewed before posting.

## 6. RD purchase accounting

A typical taxable purchase may produce:

```text
Purchase / Inventory A/c Dr
Input CGST A/c            Dr
Input SGST A/c            Dr
    To Supplier A/c           Cr
```

The purchase module invokes the accounting engine. It must not directly maintain a separate supplier balance.

## 7. Expense capture

Supported expense categories include:

- electricity
- telephone/internet
- rent
- advertising
- courier
- repairs
- packaging
- office supplies
- travel
- professional fees
- CA/accounting fees
- bank charges
- payment gateway charges
- miscellaneous

A document may be classified using rules, but the user can override the suggestion before approval.

## 8. Smart classification

Example rules:

```text
Jio / telecom provider
    -> Telephone & Internet Expense

Electricity Board
    -> Electricity Expense

Google Ads
    -> Advertising Expense

Bank
    -> Bank Charges
```

Rules should generate suggestions, not silently post accounting.

## 9. GST-aware expense posting

A GST invoice should preserve the tax components separately.

Example:

```text
Expense A/c       Dr 100,000
Input CGST A/c    Dr   9,000
Input SGST A/c    Dr   9,000
    To Supplier A/c   118,000
```

The system must not collapse the full invoice amount into the expense ledger when input tax is separately claimable according to the configured accounting treatment.

## 10. Document-to-voucher linkage

A posted expense should expose:

```text
Expense Voucher EXP-000245
 |
 +-- Supplier/vendor
 +-- Accounting journal
 +-- GST details
 +-- Payment/allocation
 +-- Original invoice
 +-- Extraction/review history
 +-- Audit trail
```

The original image/PDF remains available according to role permissions.

## 11. Mobile camera

Mobile browsers may invoke the device camera through a standard file/capture input.

The captured image is uploaded securely to the server and enters the same Document Inbox workflow as a desktop upload.

No local accounting state is required.

## 12. Security

Document storage must be private by default.

Users access documents through authorized application endpoints or signed/controlled access mechanisms rather than public file URLs.

Log sensitive actions such as:

- upload
- view
- download
- approve
- archive
- extraction correction
- voucher creation

## 13. Failure handling

If OCR or extraction fails:

```text
Extraction Failed
       |
       v
Manual Review
       |
       v
User enters/corrects fields
       |
       v
Approval
```

The original document is never replaced with a modified OCR output.
