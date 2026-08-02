from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "0.1.0"

    anthropic_api_key: str = ""
    # Cheaper hosted LLMs reached through LiteLLM. Set a key to enable, then
    # reference e.g. `openrouter/z-ai/glm-4.6` or `deepseek/deepseek-chat` as a
    # profile primary/fallback in ai_routing.yaml. OpenRouter is one key for many
    # models (GLM, DeepSeek, Qwen, ...).
    openrouter_api_key: str = ""
    deepseek_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ai_routing_path: str = "app/config/ai_routing.yaml"
    # Learned routing weights from offline model eval (BanditPolicy). Absent by
    # default -> router uses the static ai_routing.yaml order (no behavior change).
    model_weights_path: str = "data/model_weights.json"

    database_url: str = "sqlite+aiosqlite:///./data/tef.db"
    jwt_secret: str = "dev-only-change-me"

    # Invite-code signup (closed group). Comma-separated allowed codes.
    invite_codes: str = ""
    # Public base URL used to build shareable invite links, e.g.
    # https://tef.example.com -> https://tef.example.com/signup?invite=<token>.
    # Falls back to a bare "/signup?invite=<token>" path when unset.
    public_base_url: str = ""

    # Per-user daily token budgets for metered AI features (cost guard, R7).
    tutor_daily_token_budget: int = 50000
    writing_daily_token_budget: int = 100000
    speaking_daily_token_budget: int = 60000

    # Speech (Phase 4): "disabled" until local models are configured on a self-host box.
    stt_backend: str = "disabled"  # disabled | faster-whisper
    tts_backend: str = "disabled"  # disabled | piper
    whisper_model: str = "large-v3"
    # STT is the main speaking-latency cost. Defaults keep the current CPU/int8
    # behavior; on a box with a GPU set whisper_device=cuda (compute_type
    # float16 or int8_float16) for a large speedup, or drop whisper_model to
    # small/medium to trade a little accuracy for speed on CPU.
    whisper_device: str = "cpu"  # cpu | cuda
    whisper_compute_type: str = "int8"  # int8 | float16 | int8_float16 | float32
    piper_voice: str = ""  # path to a Piper .onnx voice model
    # Cap the examiner reply length: replies are 2–4 sentences, so a tight cap
    # cuts generation time (esp. local Ollama) without truncating real answers.
    examiner_max_tokens: int = 220

    # Application data cache (in-process now; swap path to Redis later).
    cache_backend: str = "memory"
    cache_ttl_seconds: int = 300
    cache_max_entries: int = 1024

    # Object storage: "local" (dev) or "s3" (MinIO/R2/B2/S3). Swap via config.
    storage_backend: str = "local"
    local_storage_dir: str = "./data/assets"
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
