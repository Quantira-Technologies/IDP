"""Generate sample document images (JPEG) into the repo's assets/ folder.

These give the Ollama vision extractor and the UI real images to work with out of
the box. Content mirrors the mock extractor / sample texts so extraction + rules
produce meaningful, consistent results. Replace them with your own scans/photos
any time — the app reads whatever JPEG/PNG files live in assets/.

Run:  python backend/scripts/generate_sample_assets.py
Needs: Pillow (already in backend/requirements.txt).
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_ASSETS = os.path.abspath(os.path.join(_HERE, "..", "..", "assets"))

_W, _H = 1000, 1300
_MARGIN = 60


def _font(size: int, bold: bool = False):
    candidates = (
        ["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


_TITLE = _font(40, bold=True)
_H2 = _font(24, bold=True)
_BODY = _font(22)
_MONO = _font(20)


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (_W, _H), "white")
    return img, ImageDraw.Draw(img)


def _line(d: ImageDraw.ImageDraw, y: int, text: str, font=_BODY, x: int = _MARGIN, fill="black") -> int:
    d.text((x, y), text, font=font, fill=fill)
    return y + int(font.size * 1.7)


def _rule(d: ImageDraw.ImageDraw, y: int) -> int:
    d.line([(_MARGIN, y), (_W - _MARGIN, y)], fill="black", width=2)
    return y + 16


def _save(img: Image.Image, name: str) -> None:
    os.makedirs(_ASSETS, exist_ok=True)
    path = os.path.join(_ASSETS, name)
    img.save(path, "JPEG", quality=90)
    print("wrote", path)


def commercial_invoice():
    img, d = _canvas()
    y = _MARGIN
    d.text((_W / 2, y), "COMMERCIAL INVOICE", font=_TITLE, fill="black", anchor="ma")
    y += 80
    y = _line(d, y, "Invoice No: HCM20150907GDY        Date: 2015-09-07")
    y = _line(d, y, "Exporter: NINGBO FASTENER MFG CO., LTD")
    y = _line(d, y, "Consignee: GDYNIA, POLAND")
    y = _line(d, y, "PO Number: 4500280268        Currency: USD")
    y += 10
    y = _rule(d, y)
    y = _line(d, y, "HS Code     Description                 Qty     Unit    Amount   Duty%", font=_MONO)
    y = _line(d, y, "7318.15.00  DROP-IN ANCHOR M8X10X30    78000   29.33   2287.74  7.5", font=_MONO)
    y = _line(d, y, "7318.15.00  DROP-IN ANCHOR M10X12X40   47000   44.54   2093.38  5.0", font=_MONO)
    y = _rule(d, y)
    y = _line(d, y, "Total Quantity: 125000        Grand Total: USD 4381.12", font=_H2)
    y += 20
    y = _line(d, y, "SAY TOTAL: FOUR THOUSAND THREE HUNDRED EIGHTY ONE AND CENTS TWELVE")
    _save(img, "commercial_invoice.jpg")


def certificate_of_origin():
    img, d = _canvas()
    y = _MARGIN
    d.text((_W / 2, y), "CERTIFICATE OF ORIGIN", font=_TITLE, fill="black", anchor="ma")
    y += 70
    d.text((_W / 2, y), "Asia-Pacific Trade Agreement", font=_BODY, fill="black", anchor="ma")
    y += 60
    y = _line(d, y, "Certificate No: 01251110720001256")
    y = _line(d, y, "Exporter: NINGBO FASTENER MFG CO., LTD")
    y = _line(d, y, "Consignee: GDYNIA, POLAND")
    y = _line(d, y, "Country of Origin: CHINA        Destination: POLAND")
    y = _line(d, y, "Invoice No: HCM20150907GDY        Date: 2015-09-07")
    y += 10
    y = _rule(d, y)
    y = _line(d, y, "Tariff Item   Description                   Origin Criterion", font=_MONO)
    y = _line(d, y, "7318.15.00    DROP-IN ANCHOR ZPCR6+         A", font=_MONO)
    y = _line(d, y, "Gross Weight: 3162 KGS", font=_MONO)
    _save(img, "certificate_of_origin.jpg")


def purchase_order():
    img, d = _canvas()
    y = _MARGIN
    d.text((_W / 2, y), "PURCHASE ORDER", font=_TITLE, fill="black", anchor="ma")
    y += 80
    y = _line(d, y, "PO No: PO-88231        Date: 2026-08-01")
    y = _line(d, y, "Vendor: ACME STEEL WORKS LTD        Currency: USD")
    y += 10
    y = _rule(d, y)
    y = _line(d, y, "SKU       Description            Ordered   Unit    Amount", font=_MONO)
    y = _line(d, y, "ANC-M8    DROP-IN ANCHOR M8      100       20.00   2000.00", font=_MONO)
    y = _line(d, y, "ANC-M10   DROP-IN ANCHOR M10     100       30.00   3000.00", font=_MONO)
    y = _rule(d, y)
    y = _line(d, y, "Grand Total: USD 5000.00", font=_H2)
    _save(img, "purchase_order.jpg")


def goods_receipt_note():
    img, d = _canvas()
    y = _MARGIN
    d.text((_W / 2, y), "GOODS RECEIPT NOTE (GRN)", font=_TITLE, fill="black", anchor="ma")
    y += 80
    y = _line(d, y, "GRN No: GRN-55012        Date: 2026-08-14")
    y = _line(d, y, "PO No: PO-88231        Vendor: ACME STEEL WORKS LTD")
    y += 10
    y = _rule(d, y)
    y = _line(d, y, "SKU       Received", font=_MONO)
    y = _line(d, y, "ANC-M8    100", font=_MONO)
    y = _line(d, y, "ANC-M10   90", font=_MONO)
    _save(img, "goods_receipt_note.jpg")


def vendor_invoice():
    img, d = _canvas()
    y = _MARGIN
    d.text((_W / 2, y), "TAX INVOICE (VENDOR)", font=_TITLE, fill="black", anchor="ma")
    y += 80
    y = _line(d, y, "Invoice No: ACME-INV-7741        Date: 2026-08-16")
    y = _line(d, y, "PO No: PO-88231        Vendor: ACME STEEL WORKS LTD")
    y = _line(d, y, "Currency: USD")
    y += 10
    y = _rule(d, y)
    y = _line(d, y, "SKU       Billed    Unit    Amount", font=_MONO)
    y = _line(d, y, "ANC-M8    100       20.00   2000.00", font=_MONO)
    y = _line(d, y, "ANC-M10   100       33.00   3300.00", font=_MONO)
    y = _rule(d, y)
    y = _line(d, y, "Grand Total: USD 5300.00", font=_H2)
    _save(img, "vendor_invoice.jpg")


def gst_certificate():
    img, d = _canvas()
    y = _MARGIN
    d.text((_W / 2, y), "GST REGISTRATION CERTIFICATE", font=_H2, fill="black", anchor="ma")
    y += 70
    y = _line(d, y, "GSTIN: 27AAPFU0939F1ZV", font=_H2)
    y += 10
    y = _line(d, y, "Legal Name: USMAN CASHMERE TRADING CO")
    y = _line(d, y, "Trade Name: USMAN CASHMERE")
    y = _line(d, y, "State: MAHARASHTRA")
    y = _line(d, y, "Constitution: Partnership")
    y = _line(d, y, "Registration Date: 2019-07-01")
    _save(img, "gst_certificate.jpg")


def bank_statement():
    img, d = _canvas()
    y = _MARGIN
    d.text((_W / 2, y), "BANK STATEMENT", font=_TITLE, fill="black", anchor="ma")
    y += 80
    y = _line(d, y, "Account: XXXX-4471        Period: 2026-08        Currency: USD")
    y = _line(d, y, "Opening Balance: 10000.00        Closing Balance: 11750.00")
    y += 10
    y = _rule(d, y)
    y = _line(d, y, "Date         Description               Credit    Debit     Balance", font=_MONO)
    y = _line(d, y, "2026-08-03   CUSTOMER PAYMENT INV-201  3000.00   0.00      13000.00", font=_MONO)
    y = _line(d, y, "2026-08-11   SUPPLIER PAYMENT ACME     0.00      1250.00   11750.00", font=_MONO)
    _save(img, "bank_statement.jpg")


def main() -> None:
    commercial_invoice()
    certificate_of_origin()
    purchase_order()
    goods_receipt_note()
    vendor_invoice()
    gst_certificate()
    bank_statement()


if __name__ == "__main__":
    main()
