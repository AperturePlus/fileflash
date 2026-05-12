from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories import AgentPlanRepository, AgentSettingsRepository, AgentWorkSessionRepository
from ..background_jobs import BackgroundJobService


class PlanService:
    def __init__(
        self,
        *,
        db: AsyncSession,
        jobs: BackgroundJobService,
        plans: AgentPlanRepository,
        settings: AgentSettingsRepository,
        work_sessions: AgentWorkSessionRepository,
    ) -> None:
        self.db = db
        self.jobs = jobs
        self.plans = plans
        self.settings = settings
        self.work_sessions = work_sessions

    async def enqueue_plan(self, *args, **kwargs):
        raise NotImplementedError("Agent plan service is scaffolded only in this stage")
