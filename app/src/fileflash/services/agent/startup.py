from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def log_agent_database_readiness(db: AsyncSession) -> None:
    """Warn when Flyway worker/agent tables are missing."""
    checks = (
        ("background_job", "V4__worker.sql"),
        ("agent_plan", "V9__agent.sql"),
    )
    for table, migration in checks:
        try:
            await db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
            await db.commit()
            logger.info("agent.db ok table=%s", table)
        except Exception as exc:
            await db.rollback()
            logger.warning(
                "agent.db MISSING table=%s — run Flyway migration %s. Error: %s",
                table,
                migration,
                exc,
            )
