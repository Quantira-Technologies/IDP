"""Sample-asset handling: list, read, and turn an image file into a RawDocument.

Assets are the JPEG/PNG document images shipped in the repo's `assets/` folder
(or any images the client drops in). The `/api/assets` endpoints let the UI show a
gallery and run the pipeline on a real image without uploading it each time.
"""
from __future__ import annotations

import mimetypes
import os

from .config import settings
from .extractors.base import RawDocument
from .samples import raw_from_upload

_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")
_PKG_DIR = os.path.dirname(__file__)


def assets_dir() -> str:
    """Resolve the assets directory across local and Docker layouts."""
    candidates = [
        settings.assets_dir,
        os.path.abspath(settings.assets_dir),
        os.path.join(_PKG_DIR, "..", "assets"),  # Docker: /app/app -> /app/assets
        os.path.join(_PKG_DIR, "..", "..", "assets"),  # local: backend/app -> repo/assets
        "/app/assets",
    ]
    for path in candidates:
        if path and os.path.isdir(path):
            return os.path.abspath(path)
    return os.path.abspath(settings.assets_dir)


def list_assets() -> list[str]:
    d = assets_dir()
    if not os.path.isdir(d):
        return []
    return sorted(
        f for f in os.listdir(d)
        if f.lower().endswith(_IMAGE_EXTS) and os.path.isfile(os.path.join(d, f))
    )


def _safe_path(name: str) -> str:
    """Resolve an asset path, rejecting traversal outside the assets dir."""
    d = assets_dir()
    # Only allow a bare filename — no directory components.
    if not name or "/" in name or "\\" in name or name != os.path.basename(name):
        raise FileNotFoundError(name)
    path = os.path.abspath(os.path.join(d, name))
    if os.path.commonpath([path, d]) != d or not os.path.isfile(path):
        raise FileNotFoundError(name)
    return path


def read_asset(name: str) -> tuple[bytes, str]:
    path = _safe_path(name)
    with open(path, "rb") as fh:
        data = fh.read()
    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return data, content_type


def raw_from_asset(name: str) -> RawDocument:
    data, content_type = read_asset(name)
    return raw_from_upload(name, data, content_type)
