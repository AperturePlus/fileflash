from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import AgentWorkSession


class AgentWorkSessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_for_job(
        self,
        *,
        job_id: int,
        user_id: int,
        status: str = "active",
        checkpoint_json: dict[str, Any] | None = None,
    ) -> AgentWorkSession:
        existing = await self.get_by_job_id(job_id=job_id)
        if existing is not None:
            return existing

        entity = AgentWorkSession(
            job_id=job_id,
            user_id=user_id,
            status=status,
            checkpoint_json=checkpoint_json or {},
        )
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_job_id(self, *, job_id: int) -> AgentWorkSession | None:
        return await self.db.scalar(select(AgentWorkSession).where(AgentWorkSession.job_id == job_id))

    async def update_checkpoint(
        self,
        *,
        job_id: int,
        checkpoint_json: dict[str, Any],
        checkpoint_at: datetime | None = None,
    ) -> AgentWorkSession | None:
        entity = await self.get_by_job_id(job_id=job_id)
        if entity is None:
            return None

        entity.checkpoint_json = checkpoint_json
        entity.checkpoint_version = int(entity.checkpoint_version or 0) + 1
        entity.last_checkpoint_at = checkpoint_at or datetime.now(UTC)
        await self.db.flush()
        return entity

    async def close_session(
        self,
        *,
        job_id: int,
        status: str = "closed",
        closed_at: datetime | None = None,
    ) -> AgentWorkSession | None:
        entity = await self.get_by_job_id(job_id=job_id)
        if entity is None:
            return None

        entity.status = status
        entity.closed_at = closed_at or datetime.now(UTC)
        await self.db.flush()
        return entity

    async def refresh_metrics(self, *, work_session_id: int) -> AgentWorkSession | None:
        await self.db.execute(
            text("SELECT agent_refresh_work_session_metrics(:work_session_id)"),
            {"work_session_id": work_session_id},
        )
        await self.db.flush()
        return await self.db.get(AgentWorkSession, work_session_id)
