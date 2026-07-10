from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...core.settings import Settings
from ...models import BackgroundJob
from ...repositories import (
    AgentChatSessionRepository,
    AgentPlanRepository,
    AgentSettingsRepository,
    AgentWorkSessionRepository,
)
from ...schemas.agent import PlanAgentRequest, PlanAgentResponse
from ..background_jobs import BackgroundJobService


class PlanService:
    def __init__(
        self,
        *,
        db: AsyncSession,
        settings: Settings,
        jobs: BackgroundJobService,
        plans: AgentPlanRepository,
        settings_repo: AgentSettingsRepository,
        work_sessions: AgentWorkSessionRepository,
        chat_sessions: AgentChatSessionRepository,
    ) -> None:
        self.db = db
        self.settings = settings
        self.jobs = jobs
        self.plans = plans
        self.settings_repo = settings_repo
        self.work_sessions = work_sessions
        self.chat_sessions = chat_sessions

    async def enqueue_plan(self, *, user_id: int, payload: PlanAgentRequest) -> PlanAgentResponse:
        if not self.settings.agent_enabled:
            raise ApiError(status_code=503, code=503, message="Agent runtime is disabled")
        if payload.hints.budget_tokens > self.settings.agent_job_max_tokens:
            raise ApiError(
                status_code=400,
                code=400,
                message="Agent token budget exceeds server limit",
            )
        if (
            not self.settings.is_development_env
            and payload.hints.max_steps > self.settings.agent_job_max_tool_calls
        ):
            raise ApiError(status_code=400, code=400, message="Agent maxSteps exceeds server limit")

        await self._enforce_limits(user_id=user_id)
        chat_session_id = _parse_chat_session_id(payload.chat_session_id)
        chat_session = await self.chat_sessions.get_active(
            chat_session_id=chat_session_id,
            user_id=user_id,
        )
        if chat_session is None:
            raise ApiError(status_code=404, code=404, message="Agent chat session not found")
        job = await self.jobs.enqueue(
            self.db,
            task_type="agent.plan",
            payload=payload.model_dump(by_alias=True),
            requested_by=user_id,
            max_attempts=1,
            priority=100,
            agent_phase="planning",
            chat_session_id=chat_session_id,
        )
        return PlanAgentResponse(
            job_id=str(job.job_id),
            status=str(job.status),
            task_type="agent.plan",
        )

    async def _enforce_limits(self, *, user_id: int) -> None:
        concurrent = await self.db.scalar(
            select(func.count(BackgroundJob.job_id)).where(
                and_(
                    BackgroundJob.requested_by == user_id,
                    BackgroundJob.task_type.in_(["agent.plan", "agent.execute"]),
                    BackgroundJob.status.in_(["pending", "running", "retrying"]),
                )
            )
        )
        if int(concurrent or 0) >= self.settings.agent_user_concurrent_limit:
            raise ApiError(status_code=429, code=429, message="Agent concurrent job limit exceeded")

        since = datetime.now(UTC) - timedelta(days=1)
        daily = await self.db.scalar(
            select(func.count(BackgroundJob.job_id)).where(
                and_(
                    BackgroundJob.requested_by == user_id,
                    BackgroundJob.task_type == "agent.plan",
                    BackgroundJob.created_at >= since,
                )
            )
        )
        if int(daily or 0) >= self.settings.agent_user_daily_limit:
            raise ApiError(status_code=429, code=429, message="Agent daily job limit exceeded")


def _parse_chat_session_id(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid chatSessionId") from exc
    if value <= 0:
        raise ApiError(status_code=400, code=400, message="Invalid chatSessionId")
    return value
