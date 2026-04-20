from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ..core.settings import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_pre_ping=True,
)
