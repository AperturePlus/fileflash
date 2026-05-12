from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import AgentPlan


class AgentPlanRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, *, values: dict[str, Any]) -> AgentPlan:
        entity = AgentPlan(**values)
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_job_id(self, *, job_id: int, user_id: int | None = None) -> AgentPlan | None:
        statement = select(AgentPlan).where(AgentPlan.job_id == job_id)
        if user_id is not None:
            statement = statement.where(AgentPlan.user_id == user_id)
        return await self.db.scalar(statement)

    async def get_for_execute_binding(self, *, job_id: int, user_id: int, plan_hash: str | None = None) -> AgentPlan | None:
        statement = select(AgentPlan).where(
            AgentPlan.job_id == job_id,
            AgentPlan.user_id == user_id,
        )
        if plan_hash is not None:
            statement = statement.where(AgentPlan.plan_hash == plan_hash)
        return await self.db.scalar(statement)
