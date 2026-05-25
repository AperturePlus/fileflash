from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_agent_execute_service, get_agent_plan_service, get_current_user
from ..core.errors import ApiError, api_success
from ..db.deps import get_db
from ..models import BackgroundJob
from ..models.tables_identity import User
from ..schemas.agent import CancelAgentResponse, ExecuteAgentRequest, PlanAgentRequest
from ..services.agent import ExecuteService, PlanService

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/plan")
async def plan_agent_task(
    payload: PlanAgentRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    plan_service: Annotated[PlanService, Depends(get_agent_plan_service)],
):
    data = await plan_service.enqueue_plan(user_id=current_user.user_id, payload=payload)
    return api_success(
        data=data.model_dump(by_alias=True),
        message="Plan job created",
    )


@router.post("/execute")
async def execute_agent_plan(
    payload: ExecuteAgentRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    execute_service: Annotated[ExecuteService, Depends(get_agent_execute_service)],
):
    data = await execute_service.enqueue_execute(user_id=current_user.user_id, payload=payload)
    return api_success(
        data=data.model_dump(by_alias=True),
        message="Execute job created",
    )


@router.post("/cancel/{job_id}")
async def cancel_agent_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        parsed_job_id = int(job_id)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid jobId") from exc
    job = await db.scalar(
        select(BackgroundJob)
        .where(
            and_(
                BackgroundJob.job_id == parsed_job_id,
                BackgroundJob.requested_by == current_user.user_id,
                BackgroundJob.task_type.in_(["agent.plan", "agent.execute"]),
            )
        )
        .with_for_update()
    )
    if job is None:
        raise ApiError(status_code=404, code=404, message="Job not found")

    canceled_at = datetime.now(UTC)
    if job.status not in {"succeeded", "failed", "canceled"}:
        job.cancel_requested_at = canceled_at
        job.status = "canceled"
        job.agent_phase = "canceled"
        job.finished_at = canceled_at
        job.updated_at = canceled_at
    await db.commit()
    await db.refresh(job)

    data = CancelAgentResponse(
        job_id=str(job.job_id),
        status=str(job.status),
        canceled_at=job.cancel_requested_at or canceled_at,
    )
    return api_success(data=data.model_dump(by_alias=True), message="Job canceled")


__all__ = ["router"]
