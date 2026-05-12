from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ..core.settings import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_pre_ping=True,
)


async def verify_database_connection() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def verify_schema_compatibility() -> None:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'user'
                  AND column_name = 'avatar'
                LIMIT 1
                """
            )
        )
        if result.scalar() != 1:
            raise RuntimeError(
                "Database schema is outdated: missing column public.user.avatar. "
                "Run Flyway migrations (at least V10__identity_avatar.sql) before starting the API."
            )
