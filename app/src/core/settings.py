from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[1] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FileFlash API"
    api_v1_prefix: str = "/api/v1"

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    ff_db_uri: str | None = Field(default=None, alias="FF_DB_URI")

    jwt_secret_key: str = Field(default="change-this-in-production-please-use-32-plus-bytes", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    refresh_cookie_name: str = "refreshToken"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: str = "lax"
    refresh_cookie_path: str = "/"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://localhost:8080"])

    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    rabbitmq_url: str | None = Field(default=None, alias="RABBITMQ_URL")

    max_failed_login_attempts: int = 5
    account_lock_minutes: int = 15
    email_verification_expire_minutes: int = 60
    password_reset_expire_minutes: int = 30

    register_rate_limit: int = 5
    register_rate_window_seconds: int = 600
    login_rate_limit: int = 10
    login_rate_window_seconds: int = 300
    forgot_password_rate_limit: int = 5
    forgot_password_rate_window_seconds: int = 600
    resend_verification_rate_limit: int = 5
    resend_verification_rate_window_seconds: int = 600

    @property
    def resolved_database_url(self) -> str:
        db_url = self.database_url or self.ff_db_uri
        if not db_url:
            raise ValueError("DATABASE_URL or FF_DB_URI environment variable is required")
        return db_url

    @property
    def async_database_url(self) -> str:
        db_url = self.resolved_database_url
        if db_url.startswith("postgres://"):
            return "postgresql+asyncpg://" + db_url[len("postgres://") :]
        if db_url.startswith("postgresql://"):
            return "postgresql+asyncpg://" + db_url[len("postgresql://") :]
        if db_url.startswith("postgresql+asyncpg://"):
            return db_url
        return db_url

    @property
    def access_token_ttl_seconds(self) -> int:
        return self.access_token_expire_minutes * 60

    @property
    def refresh_token_ttl_seconds(self) -> int:
        return self.refresh_token_expire_days * 24 * 60 * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
