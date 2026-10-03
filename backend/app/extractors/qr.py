"""QR / barcode detection — decode values and snapshot each code separately.

Only *decoded* codes are returned (never guesses), so we never surface wrong
data. Uses pyzbar (QR + 1D barcodes) with an OpenCV QR fallback, and retries on
an upscaled image to catch small/low-res codes (e.g. ZATCA e-invoice QRs).
"""
from __future__ import annotations

import base64

import numpy as np

from ..models import BoundingBox, QRCode


def _b64_png(crop) -> str | None:
    try:
        import cv2

        ok, buf = cv2.imencode(".png", crop)
        return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode("ascii") if ok else None
    except Exception:
        return None


def _crop(img, x0, y0, x1, y1):
    h, w = img.shape[:2]
    px = int((x1 - x0) * 0.08) + 6
    py = int((y1 - y0) * 0.08) + 6
    return img[max(0, y0 - py):min(h, y1 + py), max(0, x0 - px):min(w, x1 + px)]


def detect_qr_codes(image_bytes: bytes) -> list[QRCode]:
    try:
        import cv2
    except Exception:
        return []
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return []
    h, w = img.shape[:2]
    found: dict[str, QRCode] = {}

    # --- pyzbar (QR + barcodes), on original and an upscaled copy ------------ #
    try:
        from pyzbar.pyzbar import ZBarSymbol, decode as zdecode

        # Restrict to QR + common 1D barcodes (avoids noisy DataBar/DataMatrix
        # decoder assertions and speeds detection up).
        symbols = [
            ZBarSymbol.QRCODE, ZBarSymbol.CODE128, ZBarSymbol.CODE39,
            ZBarSymbol.EAN13, ZBarSymbol.EAN8, ZBarSymbol.UPCA,
            ZBarSymbol.UPCE, ZBarSymbol.I25,
        ]

        variants = [(img, 1.0)]
        if max(h, w) < 2200:
            scale = min(2.5, 2200 / max(h, w))
            variants.append((cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC), scale))
        for variant, scale in variants:
            for r in zdecode(variant, symbols=symbols):
                data = r.data.decode("utf-8", "replace") if isinstance(r.data, bytes) else str(r.data)
                if not data or data in found:
                    continue
                x0, y0 = int(r.rect.left / scale), int(r.rect.top / scale)
                x1, y1 = int((r.rect.left + r.rect.width) / scale), int((r.rect.top + r.rect.height) / scale)
                found[data] = QRCode(
                    data=data,
                    bbox=BoundingBox(page=0, x=x0 / w, y=y0 / h, width=(x1 - x0) / w, height=(y1 - y0) / h),
                    image=_b64_png(_crop(img, x0, y0, x1, y1)),
                )
    except Exception:
        pass

    # --- OpenCV QR fallback -------------------------------------------------- #
    try:
        ok, decoded, points, _ = cv2.QRCodeDetector().detectAndDecodeMulti(img)
        if ok and points is not None:
            for i, quad in enumerate(points):
                data = decoded[i] if i < len(decoded) else ""
                if not data or data in found:
                    continue
                xs = [float(p[0]) for p in quad]; ys = [float(p[1]) for p in quad]
                x0, x1 = max(0, int(min(xs))), min(w, int(max(xs)))
                y0, y1 = max(0, int(min(ys))), min(h, int(max(ys)))
                if x1 <= x0 or y1 <= y0:
                    continue
                found[data] = QRCode(
                    data=data,
                    bbox=BoundingBox(page=0, x=x0 / w, y=y0 / h, width=(x1 - x0) / w, height=(y1 - y0) / h),
                    image=_b64_png(_crop(img, x0, y0, x1, y1)),
                )
    except Exception:
        pass

    return list(found.values())
