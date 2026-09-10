# Accounting Foundation

The first accounting implementation provides chart-of-accounts primitives, financial periods, voucher types, vouchers, journal entries, journal lines, and a transactional posting service.

Posting rules:
- draft vouchers only
- open financial period only
- voucher date must fall inside the period
- at least two journal lines
- every line has exactly one positive side
- debit must equal credit and be positive
- database transaction wraps the complete post
- voucher is locked during posting
- posted voucher is not edited by the posting service

Next: tenant/branch scoping, bill-wise party subledger, payment allocations, reversal workflow, audit trail, and API serializers/views.
