from __future__ import annotations

from functools import lru_cache
from os import cpu_count
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_worker_concurrency() -> int:
    cpu_total = cpu_count() or 2
    return max(1, cpu_total - 1)


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

    jwt_secret_key: str = Field(
        default="change-this-in-production-please-use-32-plus-bytes",
        alias="JWT_SECRET_KEY",
    )
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

    worker_poll_interval_seconds: float = Field(
        default=2.0,
        alias="WORKER_POLL_INTERVAL_SECONDS",
    )
    worker_concurrency: int = Field(
        default_factory=_default_worker_concurrency,
        alias="WORKER_CONCURRENCY",
    )
    worker_task_timeout_seconds: int = Field(default=900, alias="WORKER_TASK_TIMEOUT_SECONDS")
    worker_default_max_attempts: int = Field(default=5, alias="WORKER_DEFAULT_MAX_ATTEMPTS")
    worker_retry_backoff_seconds: str = Field(
        default="30,120,600,1800,7200",
        alias="WORKER_RETRY_BACKOFF_SECONDS",
    )
    worker_queue_stream: str = Field(default="fileflash:tasks", alias="WORKER_QUEUE_STREAM")
    worker_queue_group: str = Field(default="fileflash-workers", alias="WORKER_QUEUE_GROUP")
    worker_queue_block_ms: int = Field(default=5000, alias="WORKER_QUEUE_BLOCK_MS")

    ffmpeg_binary: str = Field(default="ffmpeg", alias="FFMPEG_BINARY")
    ffprobe_binary: str = Field(default="ffprobe", alias="FFPROBE_BINARY")

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

    @property
    def worker_retry_backoff_schedule(self) -> tuple[int, ...]:
        values: list[int] = []
        for item in self.worker_retry_backoff_seconds.split(","):
            token = item.strip()
            if not token:
                continue
            try:
                seconds = int(token)
            except ValueError:
                continue
            if seconds > 0:
                values.append(seconds)
        if not values:
            return (30, 120, 600, 1800, 7200)
        return tuple(values)


@lru_cache
def get_settings() -> Settings:
    return Settings()
