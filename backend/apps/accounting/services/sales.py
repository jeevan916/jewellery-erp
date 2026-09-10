from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounting.models import Account, BillReference, Party, SalesInvoice, SalesInvoiceLine, Voucher, VoucherType
from apps.accounting.services.posting import post_voucher


class SalesPostingError(ValidationError):
    pass


ZERO = Decimal("0.0000")


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.0001"))


@transaction.atomic
def post_sales_invoice(*, invoice_id: int, financial_period_id: int, receivable_account_id: int, sales_account_id: int, cgst_account_id: int | None = None, sgst_account_id: int | None = None, igst_account_id: int | None = None):
    """Post a sales invoice into double-entry accounting and create its bill reference."""
    invoice = SalesInvoice.objects.select_for_update().select_related("customer").get(pk=invoice_id)
    if invoice.status != SalesInvoice.Status.DRAFT:
        raise SalesPostingError("Only a draft sales invoice can be posted.")
    if invoice.customer.party_type != Party.PartyType.CUSTOMER:
        raise SalesPostingError("Sales invoice party must be a customer.")
    if invoice.total_amount <= ZERO:
        raise SalesPostingError("Sales invoice total must be positive.")

    account_ids = [receivable_account_id, sales_account_id]
    for amount, account_id, label in [
        (invoice.cgst, cgst_account_id, "CGST"),
        (invoice.sgst, sgst_account_id, "SGST"),
        (invoice.igst, igst_account_id, "IGST"),
    ]:
        if amount > ZERO and not account_id:
            raise SalesPostingError(f"{label} account is required when {label} is present.")
        if account_id:
            account_ids.append(account_id)
    active_accounts = set(Account.objects.filter(id__in=account_ids, is_active=True).values_list("id", flat=True))
    missing = set(account_ids) - active_accounts
    if missing:
        raise SalesPostingError(f"Inactive or missing accounting account(s): {sorted(missing)}")

    voucher_type, _ = VoucherType.objects.get_or_create(
        code="SALES", defaults={"name": "Sales", "category": "SALES", "prefix": "INV"}
    )
    voucher = invoice.voucher
    if voucher.status != Voucher.Status.DRAFT:
        raise SalesPostingError("Sales invoice voucher must be in draft status.")

    lines = [
        {"account_id": receivable_account_id, "debit": invoice.total_amount, "narration": invoice.invoice_number},
        {"account_id": sales_account_id, "credit": invoice.taxable_value, "narration": invoice.invoice_number},
    ]
    if invoice.cgst:
        lines.append({"account_id": cgst_account_id, "credit": invoice.cgst, "narration": invoice.invoice_number})
    if invoice.sgst:
        lines.append({"account_id": sgst_account_id, "credit": invoice.sgst, "narration": invoice.invoice_number})
    if invoice.igst:
        lines.append({"account_id": igst_account_id, "credit": invoice.igst, "narration": invoice.invoice_number})

    entry = post_voucher(voucher_id=voucher.id, lines=lines, period_id=financial_period_id)

    bill = BillReference.objects.create(
        party=invoice.customer,
        voucher=voucher,
        bill_number=invoice.invoice_number,
        bill_date=invoice.invoice_date,
        due_date=invoice.due_date,
        bill_type=BillReference.BillType.RECEIVABLE,
        amount=invoice.total_amount,
        narration=invoice.narration,
    )
    invoice.status = SalesInvoice.Status.POSTED
    invoice.save(update_fields=["status"])
    return invoice, bill, entry


def create_sales_invoice(*, customer_id: int, voucher_number: str, invoice_number: str, invoice_date, due_date=None, lines: list[dict], cgst=ZERO, sgst=ZERO, igst=ZERO, narration=""):
    """Create a draft invoice; posting is a separate explicit accounting action."""
    customer = Party.objects.get(pk=customer_id)
    if customer.party_type != Party.PartyType.CUSTOMER:
        raise SalesPostingError("Sales invoice party must be a customer.")
    if not lines:
        raise SalesPostingError("At least one sales invoice line is required.")

    taxable = ZERO
    prepared = []
    for index, item in enumerate(lines, start=1):
        quantity = Decimal(str(item["quantity"]))
        rate = _money(item["rate"])
        discount = _money(item.get("discount", ZERO))
        taxable_value = _money(quantity * rate - discount)
        if quantity <= ZERO or taxable_value < ZERO:
            raise SalesPostingError("Invalid sales invoice line quantity, rate or discount.")
        taxable += taxable_value
        prepared.append({
            "line_no": index,
            "description": item["description"],
            "hsn_code": item.get("hsn_code", ""),
            "quantity": quantity,
            "rate": rate,
            "discount": discount,
            "taxable_value": taxable_value,
        })

    cgst = _money(cgst)
    sgst = _money(sgst)
    igst = _money(igst)
    total = taxable + cgst + sgst + igst
    with transaction.atomic():
        voucher_type, _ = VoucherType.objects.get_or_create(
            code="SALES", defaults={"name": "Sales", "category": "SALES", "prefix": "INV"}
        )
        voucher = Voucher.objects.create(
            voucher_type=voucher_type, number=voucher_number, voucher_date=invoice_date,
            status=Voucher.Status.DRAFT, narration=narration,
        )
        invoice = SalesInvoice.objects.create(
            customer=customer, voucher=voucher, invoice_number=invoice_number,
            invoice_date=invoice_date, due_date=due_date, taxable_value=taxable,
            cgst=cgst, sgst=sgst, igst=igst, total_amount=total, narration=narration,
        )
        for item in prepared:
            SalesInvoiceLine.objects.create(invoice=invoice, **item)
    return invoice
