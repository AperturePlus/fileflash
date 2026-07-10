from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import AgentChatSession, BackgroundJob


class AgentChatSessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, *, user_id: int, title: str) -> AgentChatSession:
        now = datetime.now(UTC)
        entity = AgentChatSession(
            user_id=user_id,
            title=title.strip()[:255] or "New session",
            archived=False,
            created_at=now,
            updated_at=now,
        )
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def list_active(self, *, user_id: int) -> list[AgentChatSession]:
        rows = await self.db.scalars(
            select(AgentChatSession)
            .where(
                and_(
                    AgentChatSession.user_id == user_id,
                    AgentChatSession.deleted_at.is_(None),
                )
            )
            .order_by(AgentChatSession.updated_at.desc(), AgentChatSession.chat_session_id.desc())
        )
        return list(rows)

    async def get_active(
        self,
        *,
        chat_session_id: int,
        user_id: int,
        for_update: bool = False,
    ) -> AgentChatSession | None:
        statement = select(AgentChatSession).where(
            and_(
                AgentChatSession.chat_session_id == chat_session_id,
                AgentChatSession.user_id == user_id,
                AgentChatSession.deleted_at.is_(None),
            )
        )
        if for_update:
            statement = statement.with_for_update()
        return await self.db.scalar(statement)

    async def update(
        self,
        *,
        entity: AgentChatSession,
        title: str | None = None,
        archived: bool | None = None,
    ) -> AgentChatSession:
        if title is not None:
            entity.title = title.strip()[:255] or entity.title
        if archived is not None:
            entity.archived = archived
        entity.updated_at = datetime.now(UTC)
        await self.db.flush()
        return entity

    async def list_jobs(self, *, chat_session_id: int) -> list[BackgroundJob]:
        rows = await self.db.scalars(
            select(BackgroundJob)
            .where(
                and_(
                    BackgroundJob.chat_session_id == chat_session_id,
                    BackgroundJob.deleted_at.is_(None),
                )
            )
            .order_by(BackgroundJob.created_at.asc(), BackgroundJob.job_id.asc())
        )
        return list(rows)

    async def attach_jobs(
        self,
        *,
        chat_session_id: int,
        user_id: int,
        job_ids: list[int],
    ) -> int:
        if not job_ids:
            return 0
        rows = await self.db.scalars(
            select(BackgroundJob).where(
                and_(
                    BackgroundJob.job_id.in_(job_ids),
                    BackgroundJob.requested_by == user_id,
                    BackgroundJob.task_type.in_(["agent.plan", "agent.execute"]),
                    BackgroundJob.deleted_at.is_(None),
                )
            )
        )
        count = 0
        for job in rows:
            if job.chat_session_id not in (None, chat_session_id):
                continue
            job.chat_session_id = chat_session_id
            job.updated_at = datetime.now(UTC)
            count += 1
        await self.db.flush()
        return count


__all__ = ["AgentChatSessionRepository"]
