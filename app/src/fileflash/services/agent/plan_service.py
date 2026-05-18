from __future__ import annotations

import logging

from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...repositories import AgentPlanRepository, AgentSettingsRepository, AgentWorkSessionRepository
from ...schemas.agent import PlanAgentRequest, PlanAgentResponse
from .guard import log_agent_settings
from .job_enqueue import AgentBackgroundJobService

logger = logging.getLogger(__name__)


class PlanService:
    def __init__(
        self,
        *,
        db: AsyncSession,
        jobs: AgentBackgroundJobService,
        plans: AgentPlanRepository,
        settings: AgentSettingsRepository,
        work_sessions: AgentWorkSessionRepository,
    ) -> None:
        self.db = db
        self.jobs = jobs
        self.plans = plans
        self.settings = settings
        self.work_sessions = work_sessions

    async def enqueue_plan(self, *, user_id: int, request: PlanAgentRequest) -> PlanAgentResponse:
        app_settings = log_agent_settings(endpoint="agent.plan")
        logger.info(
            "agent.plan enqueue user_id=%s input_len=%s policy=%s",
            user_id,
            len(request.input),
            request.execution_policy,
        )

        payload = request.model_dump(by_alias=True, mode="json")
        try:
            job = await self.jobs.enqueue_agent(
                self.db,
                task_type="agent.plan",
                payload=payload,
                requested_by=user_id,
                agent_phase="planning",
                settings=app_settings,
            )
        except ProgrammingError as exc:
            message = str(exc).lower()
            if "background_job" in message or "agent_plan" in message:
                raise ApiError(
                    status_code=503,
                    code=503,
                    message="Agent database tables are missing. Run Flyway migrations V4 (worker) and V9 (agent).",
                ) from exc
            raise
        logger.info("agent.plan job created job_id=%s status=%s phase=%s", job.job_id, job.status, job.agent_phase)
        return PlanAgentResponse(job_id=str(job.job_id), status=job.status)
