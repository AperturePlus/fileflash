from __future__ import annotations

from src.core.settings import Settings


def test_async_database_url_conversion():
    settings = Settings(FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash")
    assert settings.async_database_url == "postgresql+asyncpg://root:pwd@localhost:5432/fileflash"


def test_upload_related_settings_defaults():
    settings = Settings(FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash")
    assert settings.object_storage_bucket == "fileflash"
    assert settings.upload_chunk_size_default == 5 * 1024 * 1024
    assert settings.upload_session_ttl_seconds == 24 * 3600


def test_agent_related_settings_defaults():
    settings = Settings(FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash")
    assert settings.agent_queue_stream == "fileflash:agents"
    assert settings.agent_job_timeout_sec == 600
    assert settings.agent_tool_timeout_sec == 30
    assert settings.agent_mcp_endpoints == ()

