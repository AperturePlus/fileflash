from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...agents.harness.policy import classify_tool_risk
from ...core.errors import ApiError
from ...core.settings import Settings
from ...models import BackgroundJob
from ...repositories import AgentPlanRepository, AgentWorkSessionRepository
from ...schemas.agent import AgentProposedAction, ExecuteAgentRequest, ExecuteAgentResponse
from ..background_jobs import BackgroundJobService


class ExecuteService:
    def __init__(
        self,
        *,
        db: AsyncSession,
        settings: Settings,
        jobs: BackgroundJobService,
        plans: AgentPlanRepository,
        work_sessions: AgentWorkSessionRepository,
    ) -> None:
        self.db = db
        self.settings = settings
        self.jobs = jobs
        self.plans = plans
        self.work_sessions = work_sessions

    async def enqueue_execute(
        self,
        *,
        user_id: int,
        payload: ExecuteAgentRequest,
    ) -> ExecuteAgentResponse:
        if not self.settings.agent_enabled:
            raise ApiError(status_code=503, code=503, message="Agent runtime is disabled")

        plan_job_id = _parse_job_id(payload.plan_job_id)
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
            raise ApiError(status_code=409, code=409, message="Plan job is not ready for execution")

        plan = await self.plans.get_for_execute_binding(
            job_id=plan_job_id,
            user_id=user_id,
            plan_hash=payload.plan_hash,
        )
        if plan is None:
            raise ApiError(status_code=409, code=409, message="planHash mismatch")

        high_risk_actions = _high_risk_actions(plan.proposed_actions_json or [])
        if high_risk_actions and not payload.approval.high_risk_confirmed:
            raise ApiError(
                status_code=409,
                code=409,
                message="High-risk action requires confirmation",
                data={"highRiskActions": high_risk_actions},
            )

        idempotency_key = f"agent.execute:{plan_job_id}"
        existing_execute = await self.db.scalar(
            select(BackgroundJob).where(
                and_(
                    BackgroundJob.task_type == "agent.execute",
                    BackgroundJob.idempotency_key == idempotency_key,
                )
            )
        )
        if existing_execute is not None:
            raise ApiError(
                status_code=409,
                code=409,
                message="Plan has already been executed",
                data={
                    "jobId": str(existing_execute.job_id),
                    "status": str(existing_execute.status),
                },
            )

        job = await self.jobs.enqueue(
            self.db,
            task_type="agent.execute",
            payload=payload.model_dump(by_alias=True, mode="json"),
            idempotency_key=idempotency_key,
            requested_by=user_id,
            max_attempts=1,
            priority=100,
            agent_phase="executing",
        )
        return ExecuteAgentResponse(
            job_id=str(job.job_id),
            status=str(job.status),
            task_type="agent.execute",
        )


def _parse_job_id(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid planJobId") from exc
    if value <= 0:
        raise ApiError(status_code=400, code=400, message="Invalid planJobId")
    return value


def _high_risk_actions(raw_actions: object) -> list[dict[str, object]]:
    if not isinstance(raw_actions, list):
        return []
    risky: list[dict[str, object]] = []
    for item in raw_actions:
        if not isinstance(item, dict):
            continue
        action = AgentProposedAction.model_validate(item)
        if action.risk_level == "high" or classify_tool_risk(action.tool) == "high":
            risky.append(action.model_dump(by_alias=True))
    return risky
