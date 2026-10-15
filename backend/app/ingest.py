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
import re

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
            text, boxes = _pdf_page_text(page, with_tables=i < _MAX_TABLE_PAGES)
            # The preview shows page 1, so only its positions are kept for highlighting.
            pages.append(RawPage(i, text, boxes if i == 0 else []))
        if doc.page_count:
            pix = doc[0].get_pixmap(dpi=_PREVIEW_DPI)
            preview = pix.tobytes("png")
    finally:
        doc.close()
    return pages, preview


_MAX_TABLE_PAGES = 20
_AR_WORD = re.compile(r"[\u0600-\u06FF]{3,}")
_AR_MARK = re.compile(r"[\u064B-\u065F\u0670]")


def _has_arabic(text: str) -> bool:
    return any("\u0600" <= c <= "\u06ff" for c in text)


def _looks_reversed(text: str) -> bool:
    """Arabic stored in visual order reads backwards: 'الحساب' comes out as 'باسحلا'."""
    words = _AR_WORD.findall(text or "")
    starts = sum(1 for w in words if w.startswith(("ال", "بال", "وال", "لل")))
    ends = sum(1 for w in words if w.endswith("لا"))
    return ends >= 2 and ends > starts


def _visual_to_logical(chars: list[dict]) -> str:
    """Rebuild an Arabic line stored in visual order, keeping each accent mark on its letter.

    In visual-order storage a mark precedes its letter in the stream, so it is
    attached to the next base character before ordering clusters by position.
    """
    clusters: list[tuple[float, str]] = []
    marks = ""
    for c in chars:
        ch = c["c"]
        if _AR_MARK.match(ch):
            marks += ch
            continue
        clusters.append((c["bbox"][0], ch + marks))
        marks = ""
    if marks and clusters:
        x, text = clusters[-1]
        clusters[-1] = (x, text + marks)
    return "".join(t for _, t in sorted(clusters, key=lambda cl: cl[0]))


def _cell_text(cell_bbox, chars: list[dict]) -> str:
    """Text of one table cell rebuilt from its glyphs (lines top-to-bottom)."""
    x0, y0, x1, y1 = cell_bbox
    inside = [
        c for c in chars
        if x0 <= (c["bbox"][0] + c["bbox"][2]) / 2 <= x1 and y0 <= (c["bbox"][1] + c["bbox"][3]) / 2 <= y1
    ]
    lines: dict[int, list[dict]] = {}
    for c in inside:
        lines.setdefault(round((c["bbox"][1] + c["bbox"][3]) / 4), []).append(c)
    parts = []
    for _, line_chars in sorted(lines.items()):
        if any(_has_arabic(c["c"]) for c in line_chars):
            parts.append(_visual_to_logical(line_chars))
        else:
            parts.append("".join(c["c"] for c in sorted(line_chars, key=lambda c: c["bbox"][0])))
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _pdf_page_text(page, with_tables: bool = True) -> tuple[str, list]:
    """Page text in reading order (table rows as 'key | value') plus on-page positions.

    Some PDF generators store Arabic glyphs in visual order; for those pages each
    Arabic line is rebuilt from glyph positions so it reads correctly.
    """
    reversed_page = _looks_reversed(page.get_text("text") or "")
    pw, ph = page.rect.width or 1.0, page.rect.height or 1.0

    def norm(b) -> tuple[float, float, float, float]:
        return (b[0] / pw, b[1] / ph, b[2] / pw, b[3] / ph)

    found: list = []

    tables = []
    if with_tables:
        try:
            tables = page.find_tables().tables
        except Exception:
            tables = []

    pending = []
    page_chars: list[dict] = []
    if reversed_page and tables:
        for block in page.get_text("rawdict").get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    page_chars.extend(span.get("chars", []))
    for t in sorted(tables, key=lambda t: t.bbox[1]):
        rows = []
        if page_chars:
            extracted = [[_cell_text(cb, page_chars) if cb else "" for cb in r.cells] for r in t.rows]
        else:
            extracted = t.extract()
        for r_idx, row in enumerate(extracted):
            cell_boxes = t.rows[r_idx].cells if r_idx < len(t.rows) else []
            cells = []
            for c_idx, raw_cell in enumerate(row):
                cell = (raw_cell or "").replace("\n", " ").strip()
                if not cell:
                    continue
                cells.append(cell)
                if c_idx < len(cell_boxes) and cell_boxes[c_idx]:
                    found.append((cell, norm(cell_boxes[c_idx])))
            if cells:
                rows.append("  |  ".join(cells))
        pending.append((t.bbox, rows))
    boxes = [b for b, _ in pending]

    def in_table(b) -> bool:
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        return any(x0 <= cx <= x1 and y0 <= cy <= y1 for x0, y0, x1, y1 in boxes)

    out: list[str] = []
    for block in page.get_text("rawdict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            if boxes and in_table(line["bbox"]):
                continue
            # Emit tables that start above this line, keeping the natural reading order.
            while pending and pending[0][0][1] <= line["bbox"][1]:
                out.extend(pending.pop(0)[1])
            chars = [c for s in line.get("spans", []) for c in s.get("chars", [])]
            if reversed_page and any(_has_arabic(c["c"]) for c in chars):
                text = _visual_to_logical(chars)
            else:
                text = "".join(c["c"] for c in chars)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                out.append(text)
                found.append((text, norm(line["bbox"])))
    for _, rows in pending:
        out.extend(rows)
    return "\n".join(out), found


def _docx_lines(content: bytes) -> list[str]:
    """DOCX content in document order: paragraphs, and table rows as 'key | value'."""
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(io.BytesIO(content))
    lines: list[str] = []
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            t = Paragraph(child, document).text.strip()
            if t:
                lines.append(t)
        elif tag == "tbl":
            for row in Table(child, document).rows:
                cells = [c.text.strip() for c in row.cells]
                # Collapse duplicate merged cells, keep order.
                seen: list[str] = []
                for c in cells:
                    if c and (not seen or seen[-1] != c):
                        seen.append(c)
                if seen:
                    lines.append("  |  ".join(seen))
    return lines


def _docx_text(content: bytes) -> str:
    return "\n".join(_docx_lines(content))


_PAGE_CSS = """
body { font-family: sans-serif; font-size: 10.5pt; color: #1d2a30; }
h1 { text-align: center; font-size: 17pt; margin: 0 0 6pt 0; }
p { margin: 3pt 0; }
table { width: 100%; border-collapse: collapse; margin: 8pt 0; }
td { border: 1px solid #b9c6cc; padding: 5pt 7pt; }
"""


def render_text_page(lines: list[str]) -> tuple[bytes | None, list]:
    """Draw document lines (tables as 'a | b' rows) as page 1 of a real page image.

    Returns the PNG and the on-page position of every line / table cell, so
    extracted values can be highlighted on it. Used for DOCX and plain-text files.
    """
    import html

    import pymupdf

    if not lines:
        return None, []
    texts: dict[str, str] = {}
    parts: list[str] = []
    table: list[list[str]] = []

    def esc(s: str) -> str:
        return html.escape(s, quote=True)

    def direction(s: str) -> str:
        return " dir='rtl'" if _has_arabic(s) else ""

    def flush_table() -> None:
        if not table:
            return
        rtl = any(_has_arabic(c) for row in table for c in row)
        rows = []
        for row in table:
            cells = []
            for cell in row:
                cid = f"e{len(texts)}"
                texts[cid] = cell
                cells.append(f"<td id='{cid}'>{esc(cell)}</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
        parts.append(f"<table{' dir=' + chr(39) + 'rtl' + chr(39) if rtl else ''}>" + "".join(rows) + "</table>")
        table.clear()

    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.split("|") if c.strip()] if "|" in line else []
        if cells:
            if table and len(table[-1]) != len(cells):
                flush_table()
            table.append(cells)
            continue
        flush_table()
        pid = f"e{len(texts)}"
        texts[pid] = line
        tag = "h1" if i == 0 else "p"
        parts.append(f"<{tag} id='{pid}'{direction(line)}>{esc(line)}</{tag}>")
    flush_table()

    rect = pymupdf.paper_rect("a4")
    positions: list = []

    def record(pos) -> None:
        if pos.open_close & 1 and pos.id in texts and getattr(pos, "page", 0) == 0:
            positions.append((texts[pos.id], pos.rect))

    buf = io.BytesIO()
    writer = pymupdf.DocumentWriter(buf)
    story = pymupdf.Story(html="".join(parts), user_css=_PAGE_CSS)
    page_no, more = 0, True
    while more and page_no < 50:
        device = writer.begin_page(rect)
        more, _ = story.place(rect + (40, 40, -40, -40))
        story.element_positions(record, {"page": page_no})
        story.draw(device)
        writer.end_page()
        page_no += 1
    writer.close()

    doc = pymupdf.open("pdf", buf.getvalue())
    try:
        png = doc[0].get_pixmap(dpi=_PREVIEW_DPI).tobytes("png")
    finally:
        doc.close()
    w, h = rect.width, rect.height
    boxes = [(t, (r[0] / w, r[1] / h, r[2] / w, r[3] / h)) for t, r in positions]
    return png, boxes


def preview_png(filename: str, content: bytes, content_type: str | None = None) -> tuple[bytes, str] | None:
    """Page-1 picture of an upload, fast, for showing the document while it is analysed."""
    kind = _sniff(content)
    if kind == "image":
        return content, content_type if content_type and content_type.startswith("image/") else "image/jpeg"
    try:
        if kind == "pdf":
            import pymupdf

            doc = pymupdf.open(stream=content, filetype="pdf")
            try:
                return doc[0].get_pixmap(dpi=_PREVIEW_DPI).tobytes("png"), "image/png"
            finally:
                doc.close()
        if kind == "docx":
            png, _ = render_text_page(_docx_lines(content))
            return (png, "image/png") if png else None
    except Exception:
        return None
    return None


def _sniff(content: bytes) -> str | None:
    """Real file type from the bytes, independent of the (possibly wrong) extension."""
    head = content[:1024]
    if b"%PDF" in head:
        return "pdf"
    if head.startswith(b"PK\x03\x04") and b"word/" in content[:65536]:
        return "docx"
    try:
        from PIL import Image

        with Image.open(io.BytesIO(content)) as img:
            img.verify()
        return "image"
    except Exception:
        return None


def _plain_text(content: bytes) -> str:
    """Decode genuine text files; binary data yields an empty string."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return ""
    printable = sum(1 for c in text if c.isprintable() or c in "\r\n\t")
    return text if text and printable / len(text) > 0.95 else ""


def ingest_upload(filename: str, content: bytes, content_type: str | None = None) -> RawDocument:
    """Build a RawDocument from real uploaded bytes (no canned content).

    Anything unreadable becomes an empty document so it goes to human review —
    never sample data.
    """
    name = filename or "document"
    kind = _sniff(content)

    if kind == "image":
        return RawDocument(
            name=name, image_bytes=content, content_type=content_type or "image/jpeg", from_upload=True, kind="image"
        )

    if kind == "pdf":
        try:
            pages, preview = _pdf_pages_and_preview(content)
        except Exception:
            pages, preview = [], None
        joined = "\n".join(p.text for p in pages)
        # Text layer is trusted once Arabic ordering is restored; otherwise OCR the page.
        native = len(joined.strip()) > 30 and not _looks_reversed(joined)
        return RawDocument(
            name=name,
            pages=pages if native else [],
            image_bytes=preview,
            content_type="image/png" if preview else None,
            text_is_native=native,
            from_upload=True,
            kind="pdf",
        )

    if kind == "docx":
        try:
            lines = _docx_lines(content)
        except Exception:
            lines = []
        text = "\n".join(lines)
        try:
            preview, boxes = render_text_page(lines)
        except Exception:
            preview, boxes = None, []
        return RawDocument(
            name=name,
            pages=[RawPage(0, text, boxes)],
            text_is_native=bool(text.strip()),
            from_upload=True,
            kind="docx",
            preview=preview,
        )

    # Plain text (e.g. .txt / .csv) is read as-is; anything else is unreadable.
    text = "" if _is_image(filename, content_type) or _is_pdf(filename, content_type) or _is_docx(filename, content_type) else _plain_text(content)
    return RawDocument(
        name=name, pages=[RawPage(0, text)], text_is_native=bool(text.strip()), from_upload=True, kind="text"
    )
