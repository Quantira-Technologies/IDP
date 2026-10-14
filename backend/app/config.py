"""Application configuration loaded from environment / .env."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # mock | ocr | auto | ollama | ollama_text. "auto" = real OCR/PDF/DOCX extraction,
    # the safe default for deployments where no .env is shipped.
    extractor: str = "auto"

    # Fields / documents scoring below this are routed to human review.
    confidence_threshold: float = 0.80

    database_url: str = "sqlite:///./storage/intel2doc.sqlite3"

    # Optional API key. When unset (default) the API is open — convenient for
    # offline demos. When set, every non-health endpoint requires it via either
    # `Authorization: Bearer <key>` or the `X-API-Key` header.
    api_key: str | None = None

    # Comma-separated list of allowed CORS origins. "*" (default) is fine for a
    # local demo; lock this down to your UI origin in production.
    cors_origins: str = "*"

    # ---- Authentication & RBAC ---- #
    # When true, protected endpoints require a valid bearer token + permission.
    auth_enabled: bool = True
    # Secret used to sign session tokens (HMAC). Override in .env for real deploys.
    auth_secret: str = "intel2doc-dev-secret-change-me"
    # Token lifetime in seconds (default 12h).
    token_ttl: int = 43200
    # Provisioned SSO (native/OIDC) — wired to a mock IdP for the POC.
    sso_enabled: bool = True
    sso_provider_label: str = "Nafath / Azure AD (SSO)"

    # ---- Ollama / AI gateway extraction ---- #
    # Works with a local Ollama server OR a hosted, OpenAI/Ollama-compatible
    # gateway (e.g. https://ai.quantrexfintech.com). The native chat path is
    # `<host>/api/chat`; the OpenAI-compatible base is `<host>/v1`.
    #   EXTRACTOR=ollama       -> vision model reads the image directly (e.g. qwen2.5vl:3b)
    #   EXTRACTOR=ollama_text  -> OCR (Tesseract) -> text chat model (e.g. qwen2.5:1.5b)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5vl:3b"
    ollama_timeout: float = 120.0
    # Bearer token for a hosted gateway. Leave unset for a local Ollama server.
    ollama_api_key: str | None = None

    # Folder of sample document images used by the /api/assets endpoints.
    assets_dir: str = "../assets"

    # Only used when extractor == "llm".
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_endpoint: str | None = None
    llm_model: str | None = None


settings = Settings()
