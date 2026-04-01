from __future__ import annotations

from src.core.settings import Settings


def test_async_database_url_conversion():
    settings = Settings(FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash")
    assert settings.async_database_url == "postgresql+asyncpg://root:pwd@localhost:5432/fileflash"

