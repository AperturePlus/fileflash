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
        env_file=str(Path(__file__).resolve().parents[3] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FileFlash API"
    api_v1_prefix: str = "/api/v1"
    app_env: str = Field(default="production", alias="APP_ENV")

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    ff_db_uri: str | None = Field(default=None, alias="FF_DB_URI")

    jwt_secret_key: str = Field(
        default="change-this-in-production-please-use-32-plus-bytes",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 3
    refresh_token_expire_days: int = 7

    refresh_cookie_name: str = "refreshToken"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: str = "lax"
    refresh_cookie_path: str = "/"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://localhost:8080"])

    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    rabbitmq_url: str | None = Field(default=None, alias="RABBITMQ_URL")

    object_storage_endpoint: str = Field(default="localhost:9000", alias="OBJECT_STORAGE_ENDPOINT")
    object_storage_access_key: str = Field(default="admin", alias="OBJECT_STORAGE_ACCESS_KEY")
    object_storage_secret_key: str = Field(default="minio-admin", alias="OBJECT_STORAGE_SECRET_KEY")
    object_storage_bucket: str = Field(default="fileflash", alias="OBJECT_STORAGE_BUCKET")
    object_storage_secure: bool = Field(default=False, alias="OBJECT_STORAGE_SECURE")
    object_storage_region: str | None = Field(default=None, alias="OBJECT_STORAGE_REGION")

    upload_chunk_size_default: int = Field(default=5 * 1024 * 1024, alias="UPLOAD_CHUNK_SIZE_DEFAULT")
    upload_chunk_size_min: int = Field(default=1 * 1024 * 1024, alias="UPLOAD_CHUNK_SIZE_MIN")
    upload_chunk_size_max: int = Field(default=16 * 1024 * 1024, alias="UPLOAD_CHUNK_SIZE_MAX")
    upload_single_file_size_max: int = Field(default=5 * 1024 * 1024 * 1024, alias="UPLOAD_SINGLE_FILE_SIZE_MAX")
    upload_session_ttl_hours: int = Field(default=24, alias="UPLOAD_SESSION_TTL_HOURS")
    upload_temp_prefix: str = Field(default="tmp", alias="UPLOAD_TEMP_PREFIX")
    upload_object_prefix: str = Field(default="objects", alias="UPLOAD_OBJECT_PREFIX")

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

    agent_enabled: bool = Field(default=False, alias="AGENT_ENABLED")
    agent_queue_stream: str = Field(default="fileflash:agents", alias="AGENT_QUEUE_STREAM")
    agent_queue_group: str = Field(default="fileflash-agents", alias="AGENT_QUEUE_GROUP")
    agent_queue_block_ms: int = Field(default=5000, alias="AGENT_QUEUE_BLOCK_MS")
    agent_worker_concurrency: int = Field(default=4, alias="AGENT_WORKER_CONCURRENCY")
    agent_job_timeout_sec: int = Field(default=600, alias="AGENT_JOB_TIMEOUT_SEC")
    agent_tool_timeout_sec: int = Field(default=30, alias="AGENT_TOOL_TIMEOUT_SEC")
    agent_job_max_tokens: int = Field(default=50000, alias="AGENT_JOB_MAX_TOKENS")
    agent_job_max_tool_calls: int = Field(default=100, alias="AGENT_JOB_MAX_TOOL_CALLS")
    agent_compact_threshold: float = Field(default=0.75, alias="AGENT_COMPACT_THRESHOLD")
    agent_user_daily_limit: int = Field(default=50, alias="AGENT_USER_DAILY_LIMIT")
    agent_user_concurrent_limit: int = Field(default=2, alias="AGENT_USER_CONCURRENT_LIMIT")
    agent_staging_ttl_sec: int = Field(default=86400, alias="AGENT_STAGING_TTL_SEC")
    agent_sse_enabled: bool = Field(default=False, alias="AGENT_SSE_ENABLED")
    agent_llm_provider: str = Field(default="anthropic", alias="AGENT_LLM_PROVIDER")
    agent_llm_model: str = Field(default="claude-sonnet-4-6", alias="AGENT_LLM_MODEL")
    agent_llm_api_key: str | None = Field(default=None, alias="AGENT_LLM_API_KEY")
    agent_mcp_endpoints_raw: str = Field(default="[]", alias="AGENT_MCP_ENDPOINTS")

    ffmpeg_binary: str = Field(default="ffmpeg", alias="FFMPEG_BINARY")
    ffprobe_binary: str = Field(default="ffprobe", alias="FFPROBE_BINARY")

    archive_preview_max_entries: int = Field(default=2000, alias="ARCHIVE_PREVIEW_MAX_ENTRIES")
    archive_extract_max_entries: int = Field(default=20000, alias="ARCHIVE_EXTRACT_MAX_ENTRIES")
    archive_extract_max_total_bytes: int = Field(
        default=10 * 1024 * 1024 * 1024,
        alias="ARCHIVE_EXTRACT_MAX_TOTAL_BYTES",
    )
    archive_extract_max_file_bytes: int = Field(
        default=2 * 1024 * 1024 * 1024,
        alias="ARCHIVE_EXTRACT_MAX_FILE_BYTES",
    )

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

    @property
    def upload_session_ttl_seconds(self) -> int:
        return max(1, self.upload_session_ttl_hours) * 3600

    @property
    def normalized_app_env(self) -> str:
        return self.app_env.strip().lower()

    @property
    def is_development_env(self) -> bool:
        return self.normalized_app_env in {"dev", "development", "local"}

    @property
    def is_production_env(self) -> bool:
        return self.normalized_app_env in {"prod", "production"}

    @property
    def agent_mcp_endpoints(self) -> tuple[str, ...]:
        raw = self.agent_mcp_endpoints_raw.strip()
        if not raw:
            return ()
        if raw.startswith("[") and raw.endswith("]"):
            candidates = raw.strip("[]")
            items = [item.strip().strip("'\"") for item in candidates.split(",")]
        else:
            items = [item.strip() for item in raw.split(",")]
        return tuple(item for item in items if item)


@lru_cache
def get_settings() -> Settings:
    return Settings()
