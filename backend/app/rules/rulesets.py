"""Concrete rulesets per document type / workflow.

In the product these would be authored in a no-code rule builder and stored per
tenant. Here they are plain Python for clarity and testability.
"""
from __future__ import annotations

from ..models import DocumentType, RuleResult, RuleSeverity
from .engine import Rule, RuleContext, _num, is_valid_gstin, words_to_number

_TOLERANCE = 0.02  # currency rounding tolerance


# --------------------------------------------------------------------------- #
# Commercial invoice rules
# --------------------------------------------------------------------------- #
def rule_line_totals_sum(ctx: RuleContext) -> RuleResult:
    grand = _num(ctx.extraction.fields.get("grand_total").value) if "grand_total" in ctx.extraction.fields else None
    line_sum = 0.0
    for li in ctx.extraction.line_items:
        amt = _num(li.fields["amount"].value) if "amount" in li.fields else None
        if amt is not None:
            line_sum += amt
    passed = grand is not None and abs(line_sum - grand) <= _TOLERANCE
    return RuleResult(
        rule_id="line_totals_sum",
        description="Sum of line amounts equals the grand total",
        severity=RuleSeverity.CRITICAL,
        passed=passed,
        detail=f"line_sum={line_sum:.2f} grand_total={grand}",
    )


def rule_amount_in_words_matches(ctx: RuleContext) -> RuleResult:
    grand = _num(ctx.extraction.fields.get("grand_total").value) if "grand_total" in ctx.extraction.fields else None
    words = ctx.extraction.fields.get("amount_in_words")
    parsed = words_to_number(words.value) if words else None
    passed = grand is not None and parsed is not None and abs(parsed - grand) <= _TOLERANCE
    return RuleResult(
        rule_id="amount_in_words_matches",
        description="Amount-in-words matches the numeric grand total",
        severity=RuleSeverity.WARNING,
        passed=passed,
        detail=f"words={parsed} grand_total={grand}",
    )


def rule_hs_code_duty_consistency(ctx: RuleContext) -> RuleResult:
    mismatches: list[str] = []
    checked = 0
    for i, li in enumerate(ctx.extraction.line_items):
        hs = li.fields.get("hs_code")
        applied = li.fields.get("applied_duty_rate")
        if not hs or not applied:
            continue
        expected = ctx.hs_rates.get(str(hs.value), {}).get("duty_rate")
        applied_val = _num(applied.value)
        if expected is None:
            mismatches.append(f"line {i+1}: HS {hs.value} not in rate table")
            continue
        checked += 1
        if applied_val is None or abs(applied_val - expected) > 1e-6:
            mismatches.append(
                f"line {i+1}: HS {hs.value} expects {expected}% but {applied_val}% applied"
            )
    passed = not mismatches
    return RuleResult(
        rule_id="hs_code_duty_consistency",
        description="Applied duty/tax rate matches the product's HS-code rate",
        severity=RuleSeverity.CRITICAL,
        passed=passed,
        detail="; ".join(mismatches) if mismatches else f"{checked} line(s) consistent",
    )


def rule_required_invoice_fields(ctx: RuleContext) -> RuleResult:
    required = ["invoice_number", "invoice_date", "grand_total", "currency"]
    missing = [name for name in required if not ctx.extraction.fields.get(name) or ctx.extraction.fields[name].value in (None, "")]
    return RuleResult(
        rule_id="required_invoice_fields",
        description="All required invoice header fields are present",
        severity=RuleSeverity.CRITICAL,
        passed=not missing,
        detail=f"missing={missing}" if missing else "all present",
    )


# --------------------------------------------------------------------------- #
# Certificate of Origin rules
# --------------------------------------------------------------------------- #
def rule_coo_invoice_cross_check(ctx: RuleContext) -> RuleResult:
    coo_inv = ctx.extraction.fields.get("invoice_number")
    coo_val = coo_inv.value if coo_inv else None
    invoice_numbers = []
    for sib in ctx.siblings:
        if sib.doc_type == DocumentType.COMMERCIAL_INVOICE and "invoice_number" in sib.fields:
            invoice_numbers.append(sib.fields["invoice_number"].value)
    if not invoice_numbers:
        return RuleResult(
            rule_id="coo_invoice_cross_check",
            description="Certificate of Origin references a known commercial invoice",
            severity=RuleSeverity.WARNING,
            passed=True,
            detail="no sibling invoice in bundle to cross-check",
        )
    passed = coo_val in invoice_numbers
    return RuleResult(
        rule_id="coo_invoice_cross_check",
        description="Certificate of Origin invoice number matches the bundled invoice",
        severity=RuleSeverity.CRITICAL,
        passed=passed,
        detail=f"coo_invoice={coo_val} bundle_invoices={invoice_numbers}",
    )


def rule_coo_required_fields(ctx: RuleContext) -> RuleResult:
    required = ["certificate_number", "country_of_origin", "exporter"]
    missing = [name for name in required if not ctx.extraction.fields.get(name) or ctx.extraction.fields[name].value in (None, "")]
    return RuleResult(
        rule_id="coo_required_fields",
        description="All required Certificate of Origin fields are present",
        severity=RuleSeverity.CRITICAL,
        passed=not missing,
        detail=f"missing={missing}" if missing else "all present",
    )


# --------------------------------------------------------------------------- #
# Po2Pay — three-way match (PO vs GRN vs Vendor Invoice)
# --------------------------------------------------------------------------- #
def _by_sku(extraction) -> dict:
    out = {}
    for li in extraction.line_items:
        sku = li.fields.get("sku")
        if sku is not None:
            out[str(sku.value)] = li.fields
    return out


def rule_three_way_match(ctx: RuleContext) -> RuleResult:
    """Vendor invoice lines must not bill more qty than was received (GRN) and
    unit prices must match the purchase order — the classic overbilling guard."""
    po_number = ctx.extraction.fields.get("po_number")
    po_val = po_number.value if po_number else None

    po = next(
        (s for s in ctx.siblings
         if s.doc_type == DocumentType.PURCHASE_ORDER
         and s.fields.get("po_number") and s.fields["po_number"].value == po_val),
        None,
    )
    grn = next(
        (s for s in ctx.siblings
         if s.doc_type == DocumentType.GOODS_RECEIPT_NOTE
         and s.fields.get("po_number") and s.fields["po_number"].value == po_val),
        None,
    )
    if po is None or grn is None:
        return RuleResult(
            rule_id="three_way_match",
            description="Vendor invoice matches its purchase order and goods receipt",
            severity=RuleSeverity.WARNING,
            passed=True,
            detail="no sibling PO/GRN in bundle to match against",
        )

    po_lines = _by_sku(po)
    grn_lines = _by_sku(grn)
    problems: list[str] = []
    checked = 0
    for sku, inv_fields in _by_sku(ctx.extraction).items():
        billed = _num(inv_fields["billed_qty"].value) if "billed_qty" in inv_fields else None
        price = _num(inv_fields["unit_price"].value) if "unit_price" in inv_fields else None
        received = _num(grn_lines.get(sku, {}).get("received_qty").value) if sku in grn_lines and "received_qty" in grn_lines[sku] else None
        po_price = _num(po_lines.get(sku, {}).get("unit_price").value) if sku in po_lines and "unit_price" in po_lines[sku] else None
        checked += 1
        if received is not None and billed is not None and billed > received + 1e-6:
            problems.append(f"{sku}: billed {billed} > received {received}")
        if po_price is not None and price is not None and abs(price - po_price) > _TOLERANCE:
            problems.append(f"{sku}: price {price} != PO price {po_price}")
    passed = not problems
    return RuleResult(
        rule_id="three_way_match",
        description="Vendor invoice matches its purchase order and goods receipt",
        severity=RuleSeverity.CRITICAL,
        passed=passed,
        detail="; ".join(problems) if problems else f"{checked} line(s) matched PO+GRN",
    )


def rule_required_vendor_invoice_fields(ctx: RuleContext) -> RuleResult:
    required = ["invoice_number", "po_number", "grand_total", "currency"]
    missing = [name for name in required if not ctx.extraction.fields.get(name) or ctx.extraction.fields[name].value in (None, "")]
    return RuleResult(
        rule_id="required_vendor_invoice_fields",
        description="All required vendor invoice header fields are present",
        severity=RuleSeverity.CRITICAL,
        passed=not missing,
        detail=f"missing={missing}" if missing else "all present",
    )


# --------------------------------------------------------------------------- #
# Contract Management — GST certificate
# --------------------------------------------------------------------------- #
def rule_gstin_checksum(ctx: RuleContext) -> RuleResult:
    gstin = ctx.extraction.fields.get("gstin")
    val = str(gstin.value) if gstin else None
    passed = bool(val) and is_valid_gstin(val)
    return RuleResult(
        rule_id="gstin_checksum",
        description="GSTIN is 15 chars with a valid check digit",
        severity=RuleSeverity.CRITICAL,
        passed=passed,
        detail=f"gstin={val} valid={passed}",
    )


# --------------------------------------------------------------------------- #
# Finance Operations — bank statement
# --------------------------------------------------------------------------- #
def rule_running_balance(ctx: RuleContext) -> RuleResult:
    opening = _num(ctx.extraction.fields.get("opening_balance").value) if "opening_balance" in ctx.extraction.fields else None
    closing = _num(ctx.extraction.fields.get("closing_balance").value) if "closing_balance" in ctx.extraction.fields else None
    if opening is None or closing is None:
        return RuleResult(
            rule_id="running_balance",
            description="Statement running balance reconciles opening to closing",
            severity=RuleSeverity.CRITICAL,
            passed=False,
            detail="missing opening/closing balance",
        )
    balance = opening
    problems: list[str] = []
    for i, li in enumerate(ctx.extraction.line_items):
        credit = _num(li.fields["credit"].value) if "credit" in li.fields else 0.0
        debit = _num(li.fields["debit"].value) if "debit" in li.fields else 0.0
        balance += (credit or 0.0) - (debit or 0.0)
        stated = _num(li.fields["balance"].value) if "balance" in li.fields else None
        if stated is not None and abs(stated - balance) > _TOLERANCE:
            problems.append(f"line {i+1}: running {balance:.2f} != stated {stated:.2f}")
    if abs(balance - closing) > _TOLERANCE:
        problems.append(f"final {balance:.2f} != closing {closing:.2f}")
    passed = not problems
    return RuleResult(
        rule_id="running_balance",
        description="Statement running balance reconciles opening to closing",
        severity=RuleSeverity.CRITICAL,
        passed=passed,
        detail="; ".join(problems) if problems else f"reconciles to {closing:.2f}",
    )


# --------------------------------------------------------------------------- #
# Customs — House Air Waybill
# --------------------------------------------------------------------------- #
def rule_required_hawb_fields(ctx: RuleContext) -> RuleResult:
    required = ["hawb_number", "airport_of_departure", "airport_of_destination"]
    missing = [n for n in required if not ctx.extraction.fields.get(n) or ctx.extraction.fields[n].value in (None, "")]
    return RuleResult(
        rule_id="required_hawb_fields",
        description="All required air-waybill routing fields are present",
        severity=RuleSeverity.CRITICAL,
        passed=not missing,
        detail=f"missing={missing}" if missing else "all present",
    )


def rule_hawb_weight_consistency(ctx: RuleContext) -> RuleResult:
    gross = _num(ctx.extraction.fields.get("gross_weight").value) if "gross_weight" in ctx.extraction.fields else None
    chargeable = _num(ctx.extraction.fields.get("chargeable_weight").value) if "chargeable_weight" in ctx.extraction.fields else None
    if gross is None or chargeable is None:
        return RuleResult(
            rule_id="hawb_weight_consistency",
            description="Chargeable weight is at least the gross weight",
            severity=RuleSeverity.WARNING,
            passed=True,
            detail="gross/chargeable weight not both present",
        )
    passed = chargeable + _TOLERANCE >= gross
    return RuleResult(
        rule_id="hawb_weight_consistency",
        description="Chargeable weight is at least the gross weight",
        severity=RuleSeverity.CRITICAL,
        passed=passed,
        detail=f"gross={gross} chargeable={chargeable}",
    )


# --------------------------------------------------------------------------- #
# Customs — Traveler Customs Declaration
# --------------------------------------------------------------------------- #
def rule_required_declaration_fields(ctx: RuleContext) -> RuleResult:
    required = ["first_name", "surname", "nationality", "passport_number"]
    missing = [n for n in required if not ctx.extraction.fields.get(n) or ctx.extraction.fields[n].value in (None, "")]
    return RuleResult(
        rule_id="required_declaration_fields",
        description="All required traveler identity fields are present",
        severity=RuleSeverity.CRITICAL,
        passed=not missing,
        detail=f"missing={missing}" if missing else "all present",
    )


RULESETS: dict[DocumentType, list[Rule]] = {
    DocumentType.COMMERCIAL_INVOICE: [
        rule_required_invoice_fields,
        rule_line_totals_sum,
        rule_amount_in_words_matches,
        rule_hs_code_duty_consistency,
    ],
    DocumentType.CERTIFICATE_OF_ORIGIN: [
        rule_coo_required_fields,
        rule_coo_invoice_cross_check,
    ],
    DocumentType.HOUSE_AIR_WAYBILL: [
        rule_required_hawb_fields,
        rule_hawb_weight_consistency,
    ],
    DocumentType.CUSTOMS_DECLARATION: [
        rule_required_declaration_fields,
    ],
    DocumentType.VENDOR_INVOICE: [
        rule_required_vendor_invoice_fields,
        rule_line_totals_sum,
        rule_three_way_match,
    ],
    DocumentType.GST_CERTIFICATE: [
        rule_gstin_checksum,
    ],
    DocumentType.BANK_STATEMENT: [
        rule_running_balance,
    ],
}


def rules_for(doc_type: DocumentType) -> list[Rule]:
    return RULESETS.get(doc_type, [])
