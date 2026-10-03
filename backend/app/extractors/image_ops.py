"""Image clean-up before OCR — makes blurry / pixelated / skewed scans readable.

Pipeline (OpenCV): grayscale → upscale small images → denoise → deskew →
adaptive/Otsu threshold. Every step is defensive: if anything fails we fall back
to a lighter step so OCR always gets *some* usable image.
"""
from __future__ import annotations

import io

import numpy as np


def load_bgr(image_bytes: bytes):
    import cv2

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img


def _deskew(gray):
    import cv2

    try:
        inv = cv2.bitwise_not(gray)
        thr = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thr > 0))
        if len(coords) < 50:
            return gray
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) < 0.5 or abs(angle) > 30:
            return gray  # ignore tiny/implausible skews
        (h, w) = gray.shape[:2]
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        return cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    except Exception:
        return gray


def preprocess_for_ocr(image_bytes: bytes):
    """Return a cleaned PIL.Image ready for Tesseract (or the original on failure)."""
    from PIL import Image

    try:
        import cv2

        img = load_bgr(image_bytes)
        if img is None:
            return Image.open(io.BytesIO(image_bytes)).convert("RGB")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Upscale small / low-res images so small text becomes legible.
        h, w = gray.shape[:2]
        longest = max(h, w)
        if longest < 1800:
            scale = min(3.0, 1800 / longest)
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Denoise (helps compression artefacts / pixelation) then sharpen.
        gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
        blur = cv2.GaussianBlur(gray, (0, 0), 3)
        gray = cv2.addWeighted(gray, 1.6, blur, -0.6, 0)

        gray = _deskew(gray)

        # Adaptive threshold copes with uneven lighting / shadows.
        binar = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
        )
        return Image.fromarray(binar)
    except Exception:
        try:
            return Image.open(io.BytesIO(image_bytes)).convert("L")
        except Exception:
            return Image.open(io.BytesIO(image_bytes)).convert("RGB")
