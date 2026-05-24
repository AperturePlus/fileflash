from __future__ import annotations

import pytest

from fileflash.core.settings import Settings


def test_async_database_url_conversion():
    settings = Settings(FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash")
    assert settings.async_database_url == "postgresql+asyncpg://root:pwd@localhost:5432/fileflash"


def test_upload_related_settings_defaults():
    settings = Settings(FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash")
    assert settings.object_storage_bucket == "fileflash"
    assert settings.upload_chunk_size_default == 5 * 1024 * 1024
    assert settings.upload_single_file_size_max == 20 * 1024 * 1024 * 1024
    assert settings.upload_verify_merged_object_hash is False
    assert settings.upload_session_ttl_seconds == 24 * 3600
    assert settings.starred_items_limit == 20
    assert settings.worker_process_count == 1


def test_agent_related_settings_defaults():
    settings = Settings(FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash")
    assert settings.agent_queue_stream == "fileflash:agents"
    assert settings.agent_job_timeout_sec == 600
    assert settings.agent_tool_timeout_sec == 30
    assert settings.agent_mcp_endpoints == ()


def test_app_env_detection():
    dev = Settings(FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash", APP_ENV="development")
    assert dev.is_development_env is True
    assert dev.is_production_env is False

    prod = Settings(FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash", APP_ENV="prod")
    assert prod.is_development_env is False
    assert prod.is_production_env is True


def test_worker_process_count_from_env():
    settings = Settings(
        FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash",
        WORKER_PROCESS_COUNT="3",
    )
    assert settings.worker_process_count == 3


def test_starred_items_limit_from_env():
    settings = Settings(
        FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash",
        STARRED_ITEMS_LIMIT="12",
    )
    assert settings.starred_items_limit == 12


def test_verify_base_url_defaults_to_localhost_in_development():
    settings = Settings(
        FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash",
        APP_ENV="development",
        EMAIL_VERIFY_BASE_URL="",
    )
    assert settings.normalized_email_verify_base_url == "http://localhost:8080"


def test_verify_base_url_adds_http_when_scheme_missing():
    settings = Settings(
        FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash",
        EMAIL_VERIFY_BASE_URL="localhost:3000",
    )
    assert settings.normalized_email_verify_base_url == "http://localhost:3000"


def test_mail_configuration_issues_includes_missing_required_fields():
    settings = Settings(
        FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash",
        APP_ENV="development",
        MAIL_FROM="",
        MAIL_SERVER="",
        MAIL_USERNAME="demo@example.com",
        MAIL_PASSWORD="secret",
    )
    issues = settings.mail_configuration_issues
    assert "MAIL_FROM is required" in issues
    assert "MAIL_SERVER is required" in issues
    assert settings.is_mail_configured is False


def test_mail_configuration_rejects_both_tls_modes_enabled():
    settings = Settings(
        FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash",
        EMAIL_VERIFY_BASE_URL="http://localhost:5173",
        MAIL_FROM="demo@example.com",
        MAIL_SERVER="smtp.example.com",
        MAIL_PORT=587,
        MAIL_USERNAME="demo@example.com",
        MAIL_PASSWORD="secret",
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=True,
    )
    assert "MAIL_SSL_TLS and MAIL_STARTTLS cannot both be true" in settings.mail_configuration_issues


def test_assert_runtime_security_raises_when_jwt_secret_too_short():
    settings = Settings(
        FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash",
        JWT_SECRET_KEY="short-key",
    )
    with pytest.raises(ValueError, match="JWT_SECRET_KEY must be at least 32 bytes"):
        settings.assert_runtime_security()


def test_assert_runtime_security_raises_when_token_hash_secret_too_short():
    settings = Settings(
        FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash",
        JWT_SECRET_KEY="x" * 32,
        TOKEN_HASH_SECRET="short-key",
    )
    with pytest.raises(ValueError, match="TOKEN_HASH_SECRET must be at least 32 bytes"):
        settings.assert_runtime_security()

