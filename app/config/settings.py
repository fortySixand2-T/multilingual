from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "0.1.0"

    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ai_routing_path: str = "app/config/ai_routing.yaml"

    database_url: str = "sqlite+aiosqlite:///./data/tef.db"
    jwt_secret: str = "dev-only-change-me"

    # Invite-code signup (closed group). Comma-separated allowed codes.
    invite_codes: str = ""

    # Application data cache (in-process now; swap path to Redis later).
    cache_backend: str = "memory"
    cache_ttl_seconds: int = 300
    cache_max_entries: int = 1024

    s3_endpoint_url: str | None = None
    s3_bucket: str = "tef-assets"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"

    @property
    def invite_code_set(self) -> set[str]:
        return {c.strip() for c in self.invite_codes.split(",") if c.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
