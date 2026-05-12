from __future__ import annotations

from fileflash.core.settings import Settings


def test_async_database_url_conversion():
    settings = Settings(FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash")
    assert settings.async_database_url == "postgresql+asyncpg://root:pwd@localhost:5432/fileflash"


def test_upload_related_settings_defaults():
    settings = Settings(FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash")
    assert settings.object_storage_bucket == "fileflash"
    assert settings.upload_chunk_size_default == 5 * 1024 * 1024
    assert settings.upload_session_ttl_seconds == 24 * 3600
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

