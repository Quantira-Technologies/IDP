"""Minimal Ollama / AI-gateway client (stdlib only, no extra dependencies).

Talks to either a local Ollama server or a hosted, Ollama-compatible gateway
(e.g. https://ai.quantrexfintech.com). Two call styles are supported:

  * `generate_vision(...)`  -> POST /api/generate with an image (multimodal models)
  * `generate_chat(...)`    -> POST /api/chat   with text messages (text models)

A bearer token (OLLAMA_API_KEY) is attached automatically when configured, so the
same code works for a local server (no auth) and a secured gateway.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from ..config import settings


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.ollama_api_key:
        headers["Authorization"] = f"Bearer {settings.ollama_api_key}"
    return headers


def _post(path: str, payload: dict, timeout: float) -> dict:
    url = settings.ollama_host.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted, configured host)
        return json.loads(resp.read().decode("utf-8"))


def status() -> dict:
    """Report whether the server/gateway is reachable and the model is present.

    Hosted gateways may not expose `/api/tags`; in that case `model_available`
    is reported as None (unknown) rather than False.
    """
    url = settings.ollama_host.rstrip("/") + "/api/tags"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:  # noqa: S310
            tags = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {
            "reachable": False,
            "model_available": None,
            "model": settings.ollama_model,
            "host": settings.ollama_host,
            "authenticated": bool(settings.ollama_api_key),
            "error": str(getattr(exc, "reason", exc)),
        }
    names = {m.get("name", "") for m in tags.get("models", [])}
    # Ollama lists models as "name:tag"; accept an exact or prefix match.
    wanted = settings.ollama_model
    available = wanted in names or any(n.split(":")[0] == wanted.split(":")[0] for n in names)
    return {
        "reachable": True,
        "model_available": available,
        "model": wanted,
        "host": settings.ollama_host,
        "authenticated": bool(settings.ollama_api_key),
        "installed": sorted(names),
    }


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


def generate_chat(
    messages: list[dict],
    *,
    want_json: bool = False,
    options: dict | None = None,
) -> str:
    """Run a chat completion against a text model via /api/chat; return the content.

    `messages` is the standard [{"role": "user"|"system", "content": "..."}] list.
    """
    opts = {"temperature": 0, "num_ctx": 4096, "num_predict": 1024}
    if options:
        opts.update(options)
    payload: dict = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "options": opts,
    }
    if want_json:
        payload["format"] = "json"
    result = _post("/api/chat", payload, settings.ollama_timeout)
    # Native Ollama chat shape: {"message": {"role": "...", "content": "..."}}
    message = result.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return message["content"]
    # OpenAI-compatible fallback shape: {"choices": [{"message": {"content": ...}}]}
    choices = result.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message", {})
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            return msg["content"]
    return result.get("response", "")
