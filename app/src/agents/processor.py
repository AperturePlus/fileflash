from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..core.settings import Settings, get_settings
from ..db.session import SessionLocal
from ..repositories import AgentActionLogRepository, AgentPlanRepository, AgentWorkSessionRepository
from ..schemas.agent import AgentPlanResult, PlanAgentRequest
from ..workers.agent_jobs import mark_agent_job_failed, mark_agent_job_succeeded, set_agent_phase
from ..workers.repository import mark_job_running
from .runtime.execute_runner import ExecuteRunner
from .runtime.plan_runner import PlanRunner

logger = logging.getLogger(__name__)


def schedule_agent_job(job_id: int) -> None:
    """Run agent job processing in the API process (development / no Redis)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(process_agent_job(job_id))
        return
    loop.create_task(process_agent_job(job_id), name=f"agent-job-{job_id}")


async def process_agent_job(
    job_id: int,
    *,
    session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    logger.info("agent.processor start job_id=%s", job_id)
    async with session_factory() as db:
        async with db.begin():
            message = await mark_job_running(
                db,
                job_id=job_id,
                default_max_attempts=3,
            )
        if message is None:
            return

        user_id = int(message.requested_by) if message.requested_by else None
        if user_id is None:
            async with db.begin():
                await mark_agent_job_failed(db, job_id=job_id, error_message="Missing requestedBy")
            return

        task_type = message.task_type
        payload = dict(message.payload)

    try:
        if task_type == "agent.plan":
            result, phase = await _run_plan(
                session_factory=session_factory,
                job_id=job_id,
                user_id=user_id,
                payload=payload,
                settings=settings,
            )
        elif task_type == "agent.execute":
            result, phase = await _run_execute(
                session_factory=session_factory,
                job_id=job_id,
                user_id=user_id,
                payload=payload,
                settings=settings,
            )
        else:
            raise RuntimeError(f"Unsupported agent task type: {task_type}")
    except Exception as exc:
        logger.exception("Agent job %s failed", job_id)
        async with session_factory() as db:
            async with db.begin():
                await mark_agent_job_failed(db, job_id=job_id, error_message=str(exc))
        return

    async with session_factory() as db:
        async with db.begin():
            await mark_agent_job_succeeded(db, job_id=job_id, result=result, agent_phase=phase)
    logger.info("agent.processor done job_id=%s phase=%s", job_id, phase)


async def _run_plan(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    job_id: int,
    user_id: int,
    payload: dict,
    settings: Settings,
) -> tuple[dict, str]:
    async with session_factory() as db:
        async with db.begin():
            await set_agent_phase(db, job_id=job_id, agent_phase="planning")
            runner = PlanRunner(
                db=db,
                plans=AgentPlanRepository(db),
                settings=settings,
            )
            result = await runner.run(job_id=job_id, user_id=user_id, payload=payload)

    request = PlanAgentRequest.model_validate(payload)
    plan = AgentPlanResult.model_validate(result)
    phase = "awaiting_confirm" if plan.requires_confirmation else "completed"
    if request.execution_policy == "planOnly":
        phase = "completed"
    return result, phase


async def _run_execute(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    job_id: int,
    user_id: int,
    payload: dict,
    settings: Settings,
) -> tuple[dict, str]:
    async with session_factory() as db:
        async with db.begin():
            await set_agent_phase(db, job_id=job_id, agent_phase="executing")
            runner = ExecuteRunner(
                db=db,
                plans=AgentPlanRepository(db),
                action_logs=AgentActionLogRepository(db),
                work_sessions=AgentWorkSessionRepository(db),
                allow_write_tools=settings.agent_allow_write_tools,
            )
            result = await runner.run(job_id=job_id, user_id=user_id, payload=payload)
    return result, "completed"
