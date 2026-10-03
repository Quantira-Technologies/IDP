"""Application configuration loaded from environment / .env."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "mock" (offline, deterministic) or "ollama" (real vision LLM) or "llm".
    extractor: str = "mock"

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

    # ---- Ollama vision extraction (only used when extractor == "ollama") ---- #
    # Local Ollama server and the multimodal model to use. The client wants
    # qwen2.5vl:3b — pull it once with `ollama pull qwen2.5vl:3b`.
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5vl:3b"
    ollama_timeout: float = 120.0

    # Folder of sample document images used by the /api/assets endpoints.
    assets_dir: str = "../assets"

    # Only used when extractor == "llm".
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_endpoint: str | None = None
    llm_model: str | None = None


settings = Settings()
