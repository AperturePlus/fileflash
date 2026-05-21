from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories import AgentPlanRepository, AgentWorkSessionRepository
from ..background_jobs import BackgroundJobService


class ExecuteService:
    def __init__(
        self,
        *,
        db: AsyncSession,
        jobs: BackgroundJobService,
        plans: AgentPlanRepository,
        work_sessions: AgentWorkSessionRepository,
    ) -> None:
        self.db = db
        self.jobs = jobs
        self.plans = plans
        self.work_sessions = work_sessions

    async def enqueue_execute(self, *args, **kwargs):
        raise NotImplementedError("Agent execute service is scaffolded only in this stage")
