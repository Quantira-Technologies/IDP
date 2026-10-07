"""Real document ingestion: turn an uploaded file into text + a preview image.

Supported inputs:
  * images (jpg/png/…)  -> OCR reads the bytes directly
  * PDF                 -> text layer via PyMuPDF (digital PDFs); scanned PDFs are
                           rendered to an image and OCR'd. Page 1 is rendered as a
                           preview either way.
  * DOCX                -> paragraphs + table cells via python-docx (no image)

No canned/sample text is ever injected — the pipeline sees the real content.
"""
from __future__ import annotations

import io

from .extractors.base import RawDocument, RawPage

_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")
_PREVIEW_DPI = 150


def _ext(name: str) -> str:
    name = (name or "").lower()
    return name[name.rfind(".") :] if "." in name else ""


def _is_image(filename: str, content_type: str | None) -> bool:
    if content_type and content_type.startswith("image/"):
        return True
    return _ext(filename) in _IMAGE_EXTS


def _is_pdf(filename: str, content_type: str | None) -> bool:
    return (content_type == "application/pdf") or _ext(filename) == ".pdf"


def _is_docx(filename: str, content_type: str | None) -> bool:
    if _ext(filename) == ".docx":
        return True
    return content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _pdf_pages_and_preview(content: bytes) -> tuple[list[RawPage], bytes | None]:
    """Extract text per page and render page 1 as a PNG preview."""
    import pymupdf

    pages: list[RawPage] = []
    preview: bytes | None = None
    doc = pymupdf.open(stream=content, filetype="pdf")
    try:
        for i, page in enumerate(doc):
            pages.append(RawPage(i, page.get_text("text") or ""))
        if doc.page_count:
            pix = doc[0].get_pixmap(dpi=_PREVIEW_DPI)
            preview = pix.tobytes("png")
    finally:
        doc.close()
    return pages, preview


def _docx_text(content: bytes) -> str:
    """Flatten a DOCX into text: paragraphs plus table rows as 'key | value'."""
    import docx

    document = docx.Document(io.BytesIO(content))
    lines: list[str] = []
    for para in document.paragraphs:
        t = para.text.strip()
        if t:
            lines.append(t)
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            # Collapse duplicate merged cells, keep order.
            seen: list[str] = []
            for c in cells:
                if c and (not seen or seen[-1] != c):
                    seen.append(c)
            if seen:
                lines.append("  |  ".join(seen))
    return "\n".join(lines)


def _arabic_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    arabic = sum(1 for c in letters if "\u0600" <= c <= "\u06ff")
    return arabic / len(letters)


def ingest_upload(filename: str, content: bytes, content_type: str | None = None) -> RawDocument:
    """Build a RawDocument from real uploaded bytes (no canned content)."""
    name = filename or "document"

    if _is_image(filename, content_type):
        return RawDocument(name=name, image_bytes=content, content_type=content_type or "image/jpeg")

    if _is_pdf(filename, content_type):
        try:
            pages, preview = _pdf_pages_and_preview(content)
        except Exception:
            pages, preview = [], None
        joined = "\n".join(p.text for p in pages)
        # PyMuPDF returns Arabic text in visual (reversed) order; OCR (Tesseract ara)
        # reads it correctly, so for Arabic-heavy PDFs prefer OCR on the rendered page.
        native = len(joined.strip()) > 30 and _arabic_ratio(joined) < 0.25
        return RawDocument(
            name=name,
            pages=pages if native else [],
            image_bytes=preview,
            content_type="image/png" if preview else None,
            text_is_native=native,
        )

    if _is_docx(filename, content_type):
        try:
            text = _docx_text(content)
        except Exception:
            text = ""
        return RawDocument(name=name, pages=[RawPage(0, text)], text_is_native=bool(text.strip()))

    # Unknown type: best-effort decode as UTF-8 text, else an empty document.
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = ""
    return RawDocument(name=name, pages=[RawPage(0, text)], text_is_native=bool(text.strip()))
