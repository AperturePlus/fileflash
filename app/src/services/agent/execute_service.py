from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...models import BackgroundJob
from ...repositories import AgentPlanRepository, AgentWorkSessionRepository
from ...schemas.agent import ExecuteAgentRequest, ExecuteAgentResponse
from .guard import log_agent_settings
from .job_enqueue import AgentBackgroundJobService

logger = logging.getLogger(__name__)


class ExecuteService:
    def __init__(
        self,
        *,
        db: AsyncSession,
        jobs: AgentBackgroundJobService,
        plans: AgentPlanRepository,
        work_sessions: AgentWorkSessionRepository,
    ) -> None:
        self.db = db
        self.jobs = jobs
        self.plans = plans
        self.work_sessions = work_sessions

    async def enqueue_execute(
        self,
        *,
        user_id: int,
        request: ExecuteAgentRequest,
    ) -> ExecuteAgentResponse:
        app_settings = log_agent_settings(endpoint="agent.execute")
        logger.info(
            "agent.execute enqueue user_id=%s plan_job_id=%s plan_hash_prefix=%s",
            user_id,
            request.plan_job_id,
            (request.plan_hash or "")[:16],
        )

        try:
            plan_job_id = int(request.plan_job_id)
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message="Invalid planJobId") from exc

        plan_job = await self.db.scalar(
            select(BackgroundJob).where(
                and_(
                    BackgroundJob.job_id == plan_job_id,
                    BackgroundJob.requested_by == user_id,
                    BackgroundJob.task_type == "agent.plan",
                )
            )
        )
        if plan_job is None:
            raise ApiError(status_code=404, code=404, message="Plan job not found")
        if plan_job.status != "succeeded":
            raise ApiError(
                status_code=409,
                code=409,
                message=(
                    f"Plan job is not ready for execution (current status={plan_job.status}). "
                    f"Poll GET /api/v1/jobs/{plan_job_id} until status=succeeded, "
                    "then copy result.planHash into execute body."
                ),
            )

        plan_row = await self.plans.get_for_execute_binding(
            job_id=plan_job_id,
            user_id=user_id,
            plan_hash=request.plan_hash,
        )
        if plan_row is None:
            stored_hash = str((plan_job.result or {}).get("planHash") or "")
            if stored_hash != request.plan_hash:
                raise ApiError(status_code=409, code=409, message="planHash mismatch")
        elif plan_row.plan_hash != request.plan_hash:
            raise ApiError(status_code=409, code=409, message="planHash mismatch")

        payload = request.model_dump(by_alias=True, mode="json")
        job = await self.jobs.enqueue_agent(
            self.db,
            task_type="agent.execute",
            payload=payload,
            requested_by=user_id,
            agent_phase="executing",
            settings=app_settings,
        )
        logger.info("agent.execute job created job_id=%s status=%s", job.job_id, job.status)
        return ExecuteAgentResponse(job_id=str(job.job_id), status=job.status)

    async def cancel_job(self, *, user_id: int, job_id: str) -> dict:
        from ...workers.agent_jobs import request_agent_job_cancel

        log_agent_settings(endpoint="agent.cancel")
        logger.info("agent.cancel user_id=%s job_id=%s", user_id, job_id)

        try:
            parsed = int(job_id)
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message="Invalid jobId") from exc

        job = await self.db.scalar(
            select(BackgroundJob).where(
                and_(
                    BackgroundJob.job_id == parsed,
                    BackgroundJob.requested_by == user_id,
                )
            )
        )
        if job is None:
            raise ApiError(status_code=404, code=404, message="Job not found")

        async with self.db.begin():
            job = await request_agent_job_cancel(self.db, job_id=parsed)
        if job is None:
            raise ApiError(status_code=404, code=404, message="Job not found")

        canceled_at = job.cancel_requested_at or datetime.now(UTC)
        return {
            "jobId": str(job.job_id),
            "status": job.status,
            "canceledAt": canceled_at,
        }
