"""Deterministic mock extractor.

Returns realistic, source-traced extractions for the two POC document types so the
whole pipeline can be demonstrated offline. Values mirror the shape of the sample
Commercial Invoice and Certificate of Origin. One line item carries a deliberately
inconsistent duty rate so the rules engine + routing can be shown catching a real,
factual error (not just an OCR miss).
"""
from __future__ import annotations

from ..models import BoundingBox, DocumentType, Extraction, Field, LineItem
from .base import Extractor, RawDocument


def _f(name: str, value, conf: float, page: int, x: float, y: float, w: float, h: float) -> Field:
    return Field(
        name=name,
        value=value,
        confidence=conf,
        bbox=BoundingBox(page=page, x=x, y=y, width=w, height=h),
    )


class MockExtractor(Extractor):
    name = "mock"

    def extract(self, raw: RawDocument, doc_type: DocumentType) -> Extraction:
        if doc_type == DocumentType.CERTIFICATE_OF_ORIGIN:
            return self._certificate_of_origin()
        if doc_type == DocumentType.HOUSE_AIR_WAYBILL:
            return self._house_air_waybill()
        if doc_type == DocumentType.CUSTOMS_DECLARATION:
            return self._customs_declaration()
        if doc_type == DocumentType.PURCHASE_ORDER:
            return self._purchase_order()
        if doc_type == DocumentType.GOODS_RECEIPT_NOTE:
            return self._goods_receipt_note()
        if doc_type == DocumentType.VENDOR_INVOICE:
            return self._vendor_invoice()
        if doc_type == DocumentType.GST_CERTIFICATE:
            return self._gst_certificate()
        if doc_type == DocumentType.BANK_STATEMENT:
            return self._bank_statement()
        return self._commercial_invoice()

    # ------------------------------------------------------------------ #
    def _commercial_invoice(self) -> Extraction:
        fields = {
            "invoice_number": _f("invoice_number", "HCM20150907GDY", 0.98, 0, 0.10, 0.09, 0.22, 0.03),
            "invoice_date": _f("invoice_date", "2015-09-07", 0.97, 0, 0.66, 0.09, 0.18, 0.03),
            "exporter": _f("exporter", "NINGBO FASTENER MFG CO., LTD", 0.94, 0, 0.10, 0.20, 0.35, 0.03),
            "consignee": _f("consignee", "GDYNIA, POLAND", 0.93, 0, 0.55, 0.20, 0.30, 0.03),
            "po_number": _f("po_number", "4500280268", 0.96, 0, 0.30, 0.38, 0.20, 0.03),
            "currency": _f("currency", "USD", 0.99, 0, 0.62, 0.46, 0.06, 0.03),
            "total_quantity": _f("total_quantity", 125000, 0.95, 0, 0.20, 0.62, 0.12, 0.03),
            "grand_total": _f("grand_total", 4381.12, 0.97, 0, 0.80, 0.62, 0.14, 0.03),
            "amount_in_words": _f(
                "amount_in_words",
                "FOUR THOUSAND THREE HUNDRED EIGHTY ONE AND CENTS TWELVE",
                0.88,
                0,
                0.16,
                0.72,
                0.62,
                0.03,
            ),
        }

        line_items = [
            LineItem(
                fields={
                    "description": _f("description", "STEEL DROP IN ANCHOR ZPCR6+ M8X10X30", 0.92, 0, 0.33, 0.52, 0.30, 0.02),
                    "hs_code": _f("hs_code", "7318.15.00", 0.90, 0, 0.10, 0.52, 0.12, 0.02),
                    "quantity": _f("quantity", 78000, 0.96, 0, 0.24, 0.52, 0.08, 0.02),
                    "unit_price": _f("unit_price", 29.33, 0.95, 0, 0.66, 0.52, 0.08, 0.02),
                    "amount": _f("amount", 2287.74, 0.96, 0, 0.83, 0.52, 0.10, 0.02),
                    "applied_duty_rate": _f("applied_duty_rate", 7.5, 0.85, 0, 0.94, 0.52, 0.05, 0.02),
                }
            ),
            LineItem(
                fields={
                    "description": _f("description", "STEEL DROP IN ANCHOR ZPCR6+ M10X12X40", 0.91, 0, 0.33, 0.55, 0.30, 0.02),
                    "hs_code": _f("hs_code", "7318.15.00", 0.89, 0, 0.10, 0.55, 0.12, 0.02),
                    "quantity": _f("quantity", 47000, 0.95, 0, 0.24, 0.55, 0.08, 0.02),
                    "unit_price": _f("unit_price", 44.54, 0.94, 0, 0.66, 0.55, 0.08, 0.02),
                    "amount": _f("amount", 2093.38, 0.95, 0, 0.83, 0.55, 0.10, 0.02),
                    # Deliberately inconsistent with the HS-code duty rate -> caught by rules.
                    "applied_duty_rate": _f("applied_duty_rate", 5.0, 0.83, 0, 0.94, 0.55, 0.05, 0.02),
                }
            ),
        ]

        return Extraction(
            doc_type=DocumentType.COMMERCIAL_INVOICE,
            engine=self.name,
            fields=fields,
            line_items=line_items,
        )

    # ------------------------------------------------------------------ #
    def _certificate_of_origin(self) -> Extraction:
        fields = {
            "certificate_number": _f("certificate_number", "01251110720001256", 0.95, 0, 0.55, 0.18, 0.28, 0.03),
            "exporter": _f("exporter", "NINGBO FASTENER MFG CO., LTD", 0.93, 0, 0.05, 0.10, 0.40, 0.03),
            "consignee": _f("consignee", "GDYNIA, POLAND", 0.92, 0, 0.05, 0.22, 0.35, 0.03),
            "country_of_origin": _f("country_of_origin", "CHINA", 0.98, 0, 0.10, 0.78, 0.15, 0.03),
            "destination_country": _f("destination_country", "POLAND", 0.96, 0, 0.10, 0.82, 0.15, 0.03),
            # Cross-references the commercial invoice in the same bundle.
            "invoice_number": _f("invoice_number", "HCM20150907GDY", 0.94, 0, 0.78, 0.48, 0.18, 0.03),
            "invoice_date": _f("invoice_date", "2015-09-07", 0.93, 0, 0.78, 0.51, 0.18, 0.03),
            "gross_weight": _f("gross_weight", "3162 KGS", 0.90, 0, 0.66, 0.48, 0.12, 0.03),
        }

        line_items = [
            LineItem(
                fields={
                    "hs_code": _f("hs_code", "7318.15.00", 0.90, 0, 0.05, 0.50, 0.10, 0.02),
                    "description": _f("description", "STEEL DROP IN ANCHOR ZPCR6+", 0.90, 0, 0.20, 0.50, 0.35, 0.02),
                    "origin_criterion": _f("origin_criterion", "A", 0.92, 0, 0.60, 0.50, 0.04, 0.02),
                }
            ),
        ]

        return Extraction(
            doc_type=DocumentType.CERTIFICATE_OF_ORIGIN,
            engine=self.name,
            fields=fields,
            line_items=line_items,
        )

    # ================================================================== #
    # Customs — House Air Waybill and Traveler Customs Declaration.        #
    # Mock values mirror the real sample scans so the offline demo shows   #
    # sensible data; real extraction uses the Ollama vision model.         #
    # ================================================================== #
    def _house_air_waybill(self) -> Extraction:
        fields = {
            "hawb_number": _f("hawb_number", "MHG00035659", 0.95, 0, 0.70, 0.05, 0.25, 0.03),
            "carrier": _f("carrier", "ETIHAD AIRWAYS", 0.92, 0, 0.55, 0.88, 0.30, 0.03),
            "shipper": _f("shipper", "SENATOR INTERNATIONAL", 0.88, 0, 0.05, 0.14, 0.35, 0.03),
            "consignee": _f("consignee", "BRISBANE CONSIGNEE", 0.87, 0, 0.05, 0.22, 0.35, 0.03),
            "airport_of_departure": _f("airport_of_departure", "AUH", 0.94, 0, 0.05, 0.40, 0.10, 0.03),
            "airport_of_destination": _f("airport_of_destination", "BRISBANE", 0.94, 0, 0.05, 0.46, 0.18, 0.03),
            "flight_number": _f("flight_number", "EY 002/08", 0.90, 0, 0.35, 0.40, 0.12, 0.03),
            "issue_date": _f("issue_date", "2019-09-06", 0.91, 0, 0.10, 0.90, 0.14, 0.03),
            "currency": _f("currency", "EUR", 0.98, 0, 0.55, 0.40, 0.06, 0.03),
            "terms": _f("terms", "CIF", 0.95, 0, 0.80, 0.36, 0.08, 0.03),
            "nature_of_goods": _f("nature_of_goods", "Laminates, not restricted", 0.89, 0, 0.66, 0.55, 0.30, 0.03),
            "gross_weight": _f("gross_weight", 460.0, 0.95, 0, 0.14, 0.55, 0.10, 0.03),
            "chargeable_weight": _f("chargeable_weight", 460.0, 0.94, 0, 0.40, 0.55, 0.10, 0.03),
            "declared_value_for_carriage": _f("declared_value_for_carriage", "NVD", 0.90, 0, 0.70, 0.40, 0.10, 0.03),
            "declared_value_for_customs": _f("declared_value_for_customs", "NCV", 0.90, 0, 0.85, 0.40, 0.10, 0.03),
        }
        return Extraction(doc_type=DocumentType.HOUSE_AIR_WAYBILL, engine=self.name, fields=fields, line_items=[])

    def _customs_declaration(self) -> Extraction:
        fields = {
            "first_name": _f("first_name", "AHMED", 0.93, 0, 0.10, 0.20, 0.20, 0.03),
            "father_name": _f("father_name", "SALEH", 0.90, 0, 0.55, 0.20, 0.20, 0.03),
            "surname": _f("surname", "AL-QAHTANI", 0.92, 0, 0.10, 0.26, 0.25, 0.03),
            "nationality": _f("nationality", "Saudi", 0.96, 0, 0.10, 0.32, 0.15, 0.03),
            "date_of_birth": _f("date_of_birth", "1988-04-12", 0.90, 0, 0.55, 0.32, 0.18, 0.03),
            "passport_number": _f("passport_number", "A1234567", 0.94, 0, 0.10, 0.38, 0.18, 0.03),
            "mobile": _f("mobile", "+966500000000", 0.88, 0, 0.55, 0.38, 0.20, 0.03),
            "purpose_of_travel": _f("purpose_of_travel", "Business", 0.89, 0, 0.10, 0.52, 0.20, 0.03),
            "arriving_from": _f("arriving_from", "DUBAI", 0.90, 0, 0.10, 0.58, 0.18, 0.03),
            "departing_to": _f("departing_to", "RIYADH", 0.90, 0, 0.55, 0.58, 0.18, 0.03),
            "flight_number": _f("flight_number", "EY 512", 0.88, 0, 0.10, 0.64, 0.14, 0.03),
        }
        return Extraction(doc_type=DocumentType.CUSTOMS_DECLARATION, engine=self.name, fields=fields, line_items=[])

    # ================================================================== #
    # Po2Pay workflow — Purchase Order + Goods Receipt Note + Vendor      #
    # rule can compare ordered vs received vs billed. The vendor invoice  #
    # deliberately over-bills line 2 to demo a caught factual error.      #
    # ================================================================== #
    def _purchase_order(self) -> Extraction:
        fields = {
            "po_number": _f("po_number", "PO-88231", 0.99, 0, 0.10, 0.10, 0.18, 0.03),
            "po_date": _f("po_date", "2026-08-01", 0.97, 0, 0.66, 0.10, 0.18, 0.03),
            "vendor": _f("vendor", "ACME STEEL WORKS LTD", 0.95, 0, 0.10, 0.18, 0.35, 0.03),
            "currency": _f("currency", "USD", 0.99, 0, 0.62, 0.26, 0.06, 0.03),
            "grand_total": _f("grand_total", 5000.00, 0.97, 0, 0.80, 0.62, 0.14, 0.03),
        }
        line_items = [
            LineItem(fields={
                "sku": _f("sku", "ANC-M8", 0.97, 0, 0.10, 0.40, 0.10, 0.02),
                "description": _f("description", "DROP-IN ANCHOR M8", 0.94, 0, 0.22, 0.40, 0.30, 0.02),
                "ordered_qty": _f("ordered_qty", 100, 0.98, 0, 0.55, 0.40, 0.08, 0.02),
                "unit_price": _f("unit_price", 20.00, 0.97, 0, 0.70, 0.40, 0.08, 0.02),
                "amount": _f("amount", 2000.00, 0.97, 0, 0.85, 0.40, 0.10, 0.02),
            }),
            LineItem(fields={
                "sku": _f("sku", "ANC-M10", 0.97, 0, 0.10, 0.44, 0.10, 0.02),
                "description": _f("description", "DROP-IN ANCHOR M10", 0.93, 0, 0.22, 0.44, 0.30, 0.02),
                "ordered_qty": _f("ordered_qty", 100, 0.98, 0, 0.55, 0.44, 0.08, 0.02),
                "unit_price": _f("unit_price", 30.00, 0.97, 0, 0.70, 0.44, 0.08, 0.02),
                "amount": _f("amount", 3000.00, 0.97, 0, 0.85, 0.44, 0.10, 0.02),
            }),
        ]
        return Extraction(doc_type=DocumentType.PURCHASE_ORDER, engine=self.name, fields=fields, line_items=line_items)

    def _goods_receipt_note(self) -> Extraction:
        fields = {
            "grn_number": _f("grn_number", "GRN-55012", 0.98, 0, 0.10, 0.10, 0.18, 0.03),
            "grn_date": _f("grn_date", "2026-08-14", 0.97, 0, 0.66, 0.10, 0.18, 0.03),
            "po_number": _f("po_number", "PO-88231", 0.98, 0, 0.10, 0.16, 0.18, 0.03),
            "vendor": _f("vendor", "ACME STEEL WORKS LTD", 0.94, 0, 0.10, 0.22, 0.35, 0.03),
        }
        line_items = [
            LineItem(fields={
                "sku": _f("sku", "ANC-M8", 0.97, 0, 0.10, 0.40, 0.10, 0.02),
                "received_qty": _f("received_qty", 100, 0.98, 0, 0.55, 0.40, 0.08, 0.02),
            }),
            LineItem(fields={
                "sku": _f("sku", "ANC-M10", 0.97, 0, 0.10, 0.44, 0.10, 0.02),
                # Only 90 of 100 actually received — invoice below bills for 100.
                "received_qty": _f("received_qty", 90, 0.98, 0, 0.55, 0.44, 0.08, 0.02),
            }),
        ]
        return Extraction(doc_type=DocumentType.GOODS_RECEIPT_NOTE, engine=self.name, fields=fields, line_items=line_items)

    def _vendor_invoice(self) -> Extraction:
        fields = {
            "invoice_number": _f("invoice_number", "ACME-INV-7741", 0.98, 0, 0.10, 0.10, 0.20, 0.03),
            "invoice_date": _f("invoice_date", "2026-08-16", 0.97, 0, 0.66, 0.10, 0.18, 0.03),
            "po_number": _f("po_number", "PO-88231", 0.97, 0, 0.10, 0.16, 0.18, 0.03),
            "vendor": _f("vendor", "ACME STEEL WORKS LTD", 0.95, 0, 0.10, 0.22, 0.35, 0.03),
            "currency": _f("currency", "USD", 0.99, 0, 0.62, 0.26, 0.06, 0.03),
            "grand_total": _f("grand_total", 5300.00, 0.96, 0, 0.80, 0.62, 0.14, 0.03),
        }
        line_items = [
            LineItem(fields={
                "sku": _f("sku", "ANC-M8", 0.97, 0, 0.10, 0.40, 0.10, 0.02),
                "billed_qty": _f("billed_qty", 100, 0.97, 0, 0.55, 0.40, 0.08, 0.02),
                "unit_price": _f("unit_price", 20.00, 0.96, 0, 0.70, 0.40, 0.08, 0.02),
                "amount": _f("amount", 2000.00, 0.96, 0, 0.85, 0.40, 0.10, 0.02),
            }),
            LineItem(fields={
                "sku": _f("sku", "ANC-M10", 0.97, 0, 0.10, 0.44, 0.10, 0.02),
                # Over-billed: 100 billed but only 90 received on the GRN.
                "billed_qty": _f("billed_qty", 100, 0.95, 0, 0.55, 0.44, 0.08, 0.02),
                "unit_price": _f("unit_price", 33.00, 0.94, 0, 0.70, 0.44, 0.08, 0.02),
                "amount": _f("amount", 3300.00, 0.95, 0, 0.85, 0.44, 0.10, 0.02),
            }),
        ]
        return Extraction(doc_type=DocumentType.VENDOR_INVOICE, engine=self.name, fields=fields, line_items=line_items)

    # ================================================================== #
    # Contract Management workflow — GST registration certificate.        #
    # The GSTIN carries a valid check digit so the checksum rule passes.  #
    # ================================================================== #
    def _gst_certificate(self) -> Extraction:
        fields = {
            "gstin": _f("gstin", "27AAPFU0939F1ZV", 0.96, 0, 0.10, 0.14, 0.24, 0.03),
            "legal_name": _f("legal_name", "USMAN CASHMERE TRADING CO", 0.93, 0, 0.10, 0.22, 0.40, 0.03),
            "trade_name": _f("trade_name", "USMAN CASHMERE", 0.90, 0, 0.10, 0.28, 0.30, 0.03),
            "registration_date": _f("registration_date", "2019-07-01", 0.95, 0, 0.66, 0.14, 0.18, 0.03),
            "state": _f("state", "MAHARASHTRA", 0.94, 0, 0.10, 0.34, 0.20, 0.03),
            "constitution": _f("constitution", "Partnership", 0.92, 0, 0.66, 0.28, 0.20, 0.03),
        }
        return Extraction(doc_type=DocumentType.GST_CERTIFICATE, engine=self.name, fields=fields, line_items=[])

    # ================================================================== #
    # Finance Operations workflow — bank statement. The running balance   #
    # is internally consistent so the reconciliation rule passes.         #
    # ================================================================== #
    def _bank_statement(self) -> Extraction:
        fields = {
            "account_number": _f("account_number", "XXXX-4471", 0.97, 0, 0.10, 0.10, 0.20, 0.03),
            "statement_period": _f("statement_period", "2026-08", 0.96, 0, 0.66, 0.10, 0.18, 0.03),
            "opening_balance": _f("opening_balance", 10000.00, 0.98, 0, 0.10, 0.18, 0.15, 0.03),
            "closing_balance": _f("closing_balance", 11750.00, 0.98, 0, 0.66, 0.18, 0.15, 0.03),
            "currency": _f("currency", "USD", 0.99, 0, 0.40, 0.18, 0.06, 0.03),
        }
        line_items = [
            LineItem(fields={
                "date": _f("date", "2026-08-03", 0.97, 0, 0.10, 0.40, 0.14, 0.02),
                "description": _f("description", "CUSTOMER PAYMENT INV-201", 0.92, 0, 0.26, 0.40, 0.34, 0.02),
                "credit": _f("credit", 3000.00, 0.97, 0, 0.62, 0.40, 0.10, 0.02),
                "debit": _f("debit", 0.00, 0.99, 0, 0.74, 0.40, 0.08, 0.02),
                "balance": _f("balance", 13000.00, 0.98, 0, 0.86, 0.40, 0.12, 0.02),
            }),
            LineItem(fields={
                "date": _f("date", "2026-08-11", 0.97, 0, 0.10, 0.44, 0.14, 0.02),
                "description": _f("description", "SUPPLIER PAYMENT ACME", 0.91, 0, 0.26, 0.44, 0.34, 0.02),
                "credit": _f("credit", 0.00, 0.99, 0, 0.62, 0.44, 0.10, 0.02),
                "debit": _f("debit", 1250.00, 0.97, 0, 0.74, 0.44, 0.08, 0.02),
                "balance": _f("balance", 11750.00, 0.98, 0, 0.86, 0.44, 0.12, 0.02),
            }),
        ]
        return Extraction(doc_type=DocumentType.BANK_STATEMENT, engine=self.name, fields=fields, line_items=line_items)
