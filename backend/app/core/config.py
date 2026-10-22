"""
GoaConnect Cybersecurity AI Force — Application Settings
All configuration is read from environment variables / .env file.
"""
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Core
    app_name: str = "GoaConnect Cybersecurity AI Force"
    environment: str = "development"
    debug: bool = False
    log_level: str = "info"

    # Database
    database_url: str = "postgresql+asyncpg://goauser:goapassword@localhost:5432/goaconnect"
    database_url_sync: str = "postgresql://goauser:goapassword@localhost:5432/goaconnect"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security / Auth
    secret_key: str = "change-me-in-production-must-be-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    # Rate limits
    rate_limit_per_minute: int = 60
    security_rate_limit_per_minute: int = 20

    # AI / Models
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "qwen2.5:7b"
    fast_model: str = "qwen2.5:3b"
    embedding_model: str = "nomic-embed-text"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Audit
    audit_retention_days: int = 365
    security_audit_retention_days: int = 2555

    # Optional integrations
    osiris_enabled: bool = False
    hermes_enabled: bool = False
    n8n_webhook_url: Optional[str] = None

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
