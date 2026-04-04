"""
Application settings loaded from environment variables.
Uses pydantic-settings for validation and type safety.
"""
from enum import IntEnum
from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AutonomyLevel(IntEnum):
    """Autonomy levels for agent execution."""
    ANALYSIS_ONLY = 0
    DRAFT_ONLY = 1
    APPROVAL_REQUIRED = 2
    LOW_RISK_AUTO = 3
    ADVANCED_AUTO = 4  # Disabled by default


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Core ──────────────────────────────────────────────────────────────
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    log_level: str = "INFO"
    app_name: str = "AI CMO OS"
    app_version: str = "0.1.0"

    # ─── Database ──────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://aicmo:aicmo_dev@localhost:5432/aicmo"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ─── Redis ─────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = True

    # ─── Local AI (PRIMARY) ────────────────────────────────────────────────
    # Default provider is Ollama — no external LLM API required.
    # See docs/models/local-model-stack.md
    llm_primary_provider: str = "ollama"      # "ollama" | "vllm" | "anthropic"
    ollama_base_url: str = "http://localhost:11434"
    vllm_base_url: str = "http://localhost:8001/v1"
    vllm_api_key: str = "EMPTY"
    llm_default_model: str = "qwen3:8b"       # CPU-compatible default
    llm_fast_model: str = "qwen3:8b"
    llm_reasoning_model: str = "qwen3:8b"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.3

    # ─── Embedding ─────────────────────────────────────────────────────────
    embedding_provider: str = "ollama"         # "ollama" | "sentence-transformers"
    embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768

    # ─── Qdrant ────────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # ─── Anthropic (OPTIONAL — disabled by default) ────────────────────────
    # The platform works without any external LLM API.
    anthropic_enabled: bool = False
    anthropic_api_key: str = ""

    # ─── Auth ──────────────────────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # ─── Crawling ──────────────────────────────────────────────────────────
    crawl_max_pages_default: int = 100
    crawl_delay_seconds: float = 1.0
    crawl_user_agent: str = "AiCmoBot/1.0 (growth-analysis; polite-bot)"
    crawl_timeout_seconds: int = 30
    crawl_playwright_enabled: bool = True
    crawl_blocked_domains: str = "localhost,127.0.0.1,169.254.169.254"

    @property
    def crawl_blocked_domain_list(self) -> list[str]:
        return [d.strip() for d in self.crawl_blocked_domains.split(",") if d.strip()]

    # ─── Temporal ──────────────────────────────────────────────────────────
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "ai-cmo-os"
    temporal_task_queue: str = "ai-cmo-os-queue"

    # ─── Storage ───────────────────────────────────────────────────────────
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_path: str = "./storage/artifacts"
    storage_s3_bucket: str = ""
    storage_s3_region: str = "us-east-1"

    # ─── Social OAuth ──────────────────────────────────────────────────────
    # X / Twitter — OAuth 2.0 PKCE (create app at developer.twitter.com)
    x_api_key: str = ""
    x_api_secret: str = ""
    x_callback_url: str = "http://localhost:8000/api/v1/auth/x/callback"
    # Legacy OAuth 2.0 fields (unused — kept so existing .env files don't error)
    x_client_id: str = ""
    x_client_secret: str = ""

    # Meta — Facebook Login (create app at developers.facebook.com)
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_callback_url: str = "http://localhost:3000/auth/callback/meta"

    # Google OAuth — for Google Ads (create at console.cloud.google.com)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_callback_url: str = "http://localhost:3000/auth/callback/google"
    google_ads_developer_token: str = ""

    # ─── Connectors ────────────────────────────────────────────────────────
    ga4_mock_mode: bool = True
    gsc_mock_mode: bool = True
    slack_mock_mode: bool = True
    slack_bot_token: str = ""

    # ─── Autonomy ──────────────────────────────────────────────────────────
    autonomy_default_level: int = AutonomyLevel.DRAFT_ONLY
    autonomy_max_allowed_level: int = AutonomyLevel.LOW_RISK_AUTO

    @field_validator("autonomy_default_level", "autonomy_max_allowed_level")
    @classmethod
    def validate_autonomy_level(cls, v: int) -> int:
        if not (0 <= v <= 4):
            raise ValueError(f"Autonomy level must be 0-4, got {v}")
        return v

    # ─── Twilio / Call Intelligence ────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_api_key_sid: str = ""
    twilio_api_key_secret: str = ""
    twilio_phone_number: str = ""
    twilio_twiml_app_sid: str = ""
    calls_storage_path: str = "./storage/calls"

    # ─── Demo Mode ─────────────────────────────────────────────────────────
    demo_mode: bool = False
    demo_user_email: str = "demo@aicmo.os"
    demo_user_password: str = "Demo1234!"

    # ─── Rate Limiting ─────────────────────────────────────────────────────
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 20

    # ─── Feature Flags ─────────────────────────────────────────────────────
    feature_geo_agent: bool = True
    feature_experiments: bool = True
    feature_social_publishing: bool = False
    feature_cms_publishing: bool = False
    feature_advanced_analytics: bool = False

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origins(self) -> list[str]:
        if self.is_production:
            return []  # Configure explicitly in production
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
