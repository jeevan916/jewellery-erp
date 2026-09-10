# Bill-wise and Party Accounting

## Purpose

Customer and supplier accounting must behave like a proper Tally-style sub-ledger while remaining derived from the double-entry journal.

## Party model

A party has:

- master identity
- customer/supplier classification
- contact and tax information
- one or more accounting accounts
- branch/tenant scope

The party master is not the ledger. Its linked account receives journal lines from the accounting engine.

## Bill reference

Every receivable/payable document that participates in bill-wise accounting gets a unique bill reference.

```text
Party Account
    |
    +-- Bill Reference: INV-1001
    |      original amount: 118,000
    |      allocated: 100,000
    |      outstanding: 18,000
    |
    +-- Bill Reference: INV-1002
```

Outstanding is derived from posted journal lines and explicit allocations, not from a manually editable balance field.

## Allocation rules

The system supports:

- one invoice → many payments
- one payment → many invoices
- partial allocations
- advances
- credit balances
- unallocated receipts
- allocation reversal

An allocation cannot exceed the available amount on the payment or the allocatable outstanding on the bill, subject to explicit advance handling.

## Example: partial payment

Invoice:

```text
Customer A/c Dr 118,000
    To Sales A/c 100,000
    To Output CGST A/c 9,000
    To Output SGST A/c 9,000
```

Receipt of ₹50,000:

```text
Bank A/c Dr 50,000
    To Customer A/c 50,000
```

Allocation:

```text
INV-1001
Invoice:      118,000
Allocated:     50,000
Outstanding:   68,000
```

## Example: one payment across invoices

```text
Receipt: ₹200,000

INV-1001 outstanding: ₹120,000
INV-1002 outstanding: ₹80,000
```

A single receipt can allocate:

```text
INV-1001 -> 120,000
INV-1002 ->  80,000
Total    -> 200,000
```

The journal remains one accounting event; allocations are explicit sub-ledger relationships.

## Example: overpayment

```text
Receipt: ₹150,000
Outstanding invoice: ₹118,000
Excess: ₹32,000
```

The ₹32,000 excess becomes a customer advance/credit balance according to the configured account mapping.

It must not be silently forced onto the invoice.

## Allocation reversal

If a payment was allocated to the wrong invoice:

```text
Original receipt
      |
      v
Allocation A --reverse--X
      |
      v
Allocation B --correct--> Invoice B
```

The original allocation event remains auditable.

## Supplier side

The same model applies to supplier payables:

```text
Purchase invoice
      -> Supplier payable
      -> Bill reference
      -> Payment
      -> Allocation
```

Supplier advances and debit/credit adjustments must remain traceable.

## Customer ledger drill-down

The ledger should expose:

```text
Customer Ledger
   |
   +-- Date
   +-- Voucher
   +-- Bill reference
   +-- Debit
   +-- Credit
   +-- Running balance
   |
   +-- click -> voucher
                 |
                 +-- invoice
                 +-- payment
                 +-- allocations
                 +-- journal entry
                 +-- source document
```

## Aging/outstanding

The reporting layer should be able to calculate:

- total outstanding
- current outstanding
- overdue outstanding
- bill-wise outstanding
- advances/credits
- unapplied receipts
- customer-wise and supplier-wise totals

Aging rules must be configurable rather than hard-coded to a single report format.

## Concurrency

Allocation operations are concurrency-sensitive.

Before allocating:

1. lock or otherwise safely serialize the affected payment/bill rows
2. re-read available balances
3. validate the requested allocation
4. create allocation records
5. create any required accounting adjustment
6. commit atomically

Two users must never be able to allocate the same available payment amount twice.

## Security

Party data and financial allocations are tenant/branch scoped and permission checked server-side.

The client may request an allocation but cannot determine the authoritative outstanding amount or bypass allocation validation.
