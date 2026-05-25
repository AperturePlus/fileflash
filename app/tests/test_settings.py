from __future__ import annotations

import pytest

from fileflash.core.settings import Settings


def make_settings(**overrides: object) -> Settings:
    payload = {"FF_DB_URI": "postgresql://root:pwd@localhost:5432/fileflash"}
    payload.update(overrides)
    return Settings(_env_file=None, **payload)


def test_async_database_url_conversion():
    settings = make_settings()
    assert settings.async_database_url == "postgresql+asyncpg://root:pwd@localhost:5432/fileflash"


def test_upload_related_settings_defaults():
    settings = make_settings()
    assert settings.object_storage_bucket == "fileflash"
    assert settings.upload_chunk_size_default == 5 * 1024 * 1024
    assert settings.upload_single_file_size_max == 5 * 1024 * 1024 * 1024
    assert settings.upload_verify_merged_object_hash is False
    assert settings.upload_session_ttl_seconds == 24 * 3600
    assert settings.starred_items_limit == 20
    assert settings.worker_process_count == 1


def test_agent_related_settings_defaults():
    settings = make_settings()
    assert settings.agent_queue_stream == "fileflash:agents"
    assert settings.agent_job_timeout_sec == 600
    assert settings.agent_tool_timeout_sec == 30
    assert settings.agent_mcp_endpoints == ()


def test_app_env_detection():
    dev = make_settings(APP_ENV="development")
    assert dev.is_development_env is True
    assert dev.is_production_env is False

    prod = make_settings(APP_ENV="prod")
    assert prod.is_development_env is False
    assert prod.is_production_env is True


def test_worker_process_count_from_env():
    settings = make_settings(
        WORKER_PROCESS_COUNT="3",
    )
    assert settings.worker_process_count == 3


def test_starred_items_limit_from_env():
    settings = make_settings(
        STARRED_ITEMS_LIMIT="12",
    )
    assert settings.starred_items_limit == 12


def test_verify_base_url_defaults_to_localhost_in_development():
    settings = make_settings(
        APP_ENV="development",
        EMAIL_VERIFY_BASE_URL="",
    )
    assert settings.normalized_email_verify_base_url == "http://localhost:8080"


def test_verify_base_url_adds_http_when_scheme_missing():
    settings = make_settings(
        EMAIL_VERIFY_BASE_URL="localhost:3000",
    )
    assert settings.normalized_email_verify_base_url == "http://localhost:3000"


def test_mail_configuration_issues_includes_missing_required_fields():
    settings = make_settings(
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
    settings = make_settings(
        EMAIL_VERIFY_BASE_URL="http://localhost:5173",
        MAIL_FROM="demo@example.com",
        MAIL_SERVER="smtp.example.com",
        MAIL_PORT=587,
        MAIL_USERNAME="demo@example.com",
        MAIL_PASSWORD="secret",
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=True,
    )
    assert (
        "MAIL_SSL_TLS and MAIL_STARTTLS cannot both be true"
        in settings.mail_configuration_issues
    )


def test_assert_runtime_security_raises_when_jwt_secret_too_short():
    settings = make_settings(
        APP_ENV="development",
        JWT_SECRET_KEY="short-key",
    )
    with pytest.raises(ValueError, match="JWT_SECRET_KEY must be at least 32 bytes"):
        settings.assert_runtime_security()


def test_assert_runtime_security_raises_when_token_hash_secret_too_short():
    settings = make_settings(
        APP_ENV="development",
        JWT_SECRET_KEY="x" * 32,
        TOKEN_HASH_SECRET="short-key",
    )
    with pytest.raises(ValueError, match="TOKEN_HASH_SECRET must be at least 32 bytes"):
        settings.assert_runtime_security()


def test_assert_runtime_security_requires_default_admin_env_in_production():
    settings = make_settings(
        APP_ENV="production",
        JWT_SECRET_KEY="x" * 32,
    )

    with pytest.raises(ValueError, match="DEFAULT_ADMIN_USERNAME is required in production"):
        settings.assert_runtime_security()


def test_assert_runtime_security_rejects_short_default_admin_password_in_production():
    settings = make_settings(
        APP_ENV="production",
        JWT_SECRET_KEY="x" * 32,
        DEFAULT_ADMIN_USERNAME="admin",
        DEFAULT_ADMIN_EMAIL="admin@example.com",
        DEFAULT_ADMIN_PASSWORD="short-password",
    )

    with pytest.raises(ValueError, match="DEFAULT_ADMIN_PASSWORD must be at least 32 bytes"):
        settings.assert_runtime_security()


def test_assert_runtime_security_accepts_default_admin_env_in_production():
    settings = make_settings(
        APP_ENV="production",
        JWT_SECRET_KEY="x" * 32,
        DEFAULT_ADMIN_USERNAME="admin",
        DEFAULT_ADMIN_EMAIL="admin@example.com",
        DEFAULT_ADMIN_PASSWORD="p" * 32,
    )

    settings.assert_runtime_security()

