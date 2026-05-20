from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

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
        if not await _public_table_has_column(connection, table_name="user", column_name="avatar"):
            raise RuntimeError(
                "Database schema is outdated: missing column public.user.avatar. "
                "Run Flyway migrations (at least V10__identity_avatar.sql) before starting the API."
            )
        if not await _public_table_exists(connection, table_name="registration_email_domain_rule"):
            raise RuntimeError(
                "Database schema is outdated: missing table public.registration_email_domain_rule. "
                "Run Flyway migrations (at least V11__identity_registration_email_domain_rule.sql) before starting the API."
            )


async def _public_table_has_column(connection: AsyncConnection, *, table_name: str, column_name: str) -> bool:
    result = await connection.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND column_name = :column_name
            LIMIT 1
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar() == 1


async def _public_table_exists(connection: AsyncConnection, *, table_name: str) -> bool:
    result = await connection.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND table_type = 'BASE TABLE'
            LIMIT 1
            """
        ),
        {"table_name": table_name},
    )
    return result.scalar() == 1
