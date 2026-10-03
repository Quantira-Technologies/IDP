"""Minimal Ollama client (stdlib only, no extra dependencies).

Talks to a local Ollama server for multimodal (vision) extraction with a model
such as `qwen2.5vl:3b`. Kept dependency-free so the POC stays lightweight.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from ..config import settings


def _post(path: str, payload: dict, timeout: float) -> dict:
    url = settings.ollama_host.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (local, trusted host)
        return json.loads(resp.read().decode("utf-8"))


def status() -> dict:
    """Report whether Ollama is reachable and whether the configured model exists."""
    url = settings.ollama_host.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:  # noqa: S310
            tags = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError):
        return {"reachable": False, "model_available": False, "model": settings.ollama_model}
    names = {m.get("name", "") for m in tags.get("models", [])}
    # Ollama lists models as "name:tag"; accept an exact or prefix match.
    wanted = settings.ollama_model
    available = wanted in names or any(n.split(":")[0] == wanted.split(":")[0] for n in names)
    return {"reachable": True, "model_available": available, "model": wanted, "installed": sorted(names)}


def generate_vision(prompt: str, image_bytes: bytes, want_json: bool = False) -> str:
    """Run a single vision prompt against the configured model; return raw text."""
    payload: dict = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "images": [base64.b64encode(image_bytes).decode("ascii")],
        "stream": False,
        "options": {"temperature": 0},
    }
    if want_json:
        payload["format"] = "json"
    result = _post("/api/generate", payload, settings.ollama_timeout)
    return result.get("response", "")
