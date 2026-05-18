from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_agent_execute_service, get_agent_plan_service, get_current_user, require_verified_user
from ..db.deps import get_db
from ..core.errors import api_success
from ..core.settings import get_settings
from ..services.agent.guard import AGENT_API_BUILD
from ..models.tables_identity import User
from ..schemas.agent import CancelAgentResponse, ExecuteAgentRequest, ExecuteAgentResponse, PlanAgentRequest, PlanAgentResponse
from ..services.agent.execute_service import ExecuteService
from ..services.agent.plan_service import PlanService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/jobs/{job_id}")
async def get_agent_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll agent.plan / agent.execute job status by jobId (alias of GET /api/v1/jobs/{job_id})."""
    from .jobs import get_job

    return await get_job(job_id, current_user, db)


@router.get("/status")
async def agent_status(current_user: User = Depends(get_current_user)):
    """Diagnostic: server build + Agent env flags (not a job status poll)."""
    settings = get_settings()
    return api_success(
        data={
            "build": AGENT_API_BUILD,
            "agentEnabled": settings.agent_enabled,
            "appEnv": settings.app_env,
            "agentApiActive": settings.agent_is_api_active,
            "agentInlineProcessing": settings.agent_inline_processing,
            "redisConfigured": bool(settings.redis_url),
            "userId": str(current_user.user_id),
        },
        message="Agent status",
    )


def _log_agent_request(request: Request, *, action: str, user_id: int) -> None:
    auth = request.headers.get("authorization")
    has_auth = bool(auth)
    auth_mode = "none"
    if auth:
        auth_mode = "bearer" if auth.lower().startswith("bearer ") else "raw"
    logger.info(
        "agent.http %s user_id=%s path=%s has_auth=%s auth_mode=%s",
        action,
        user_id,
        request.url.path,
        has_auth,
        auth_mode,
    )


@router.post("/plan")
async def plan_agent(
    request: Request,
    payload: PlanAgentRequest,
    current_user: User = Depends(require_verified_user),
    plan_service: PlanService = Depends(get_agent_plan_service),
):
    _log_agent_request(request, action="plan", user_id=current_user.user_id)
    data = await plan_service.enqueue_plan(user_id=current_user.user_id, request=payload)
    logger.info("agent.http plan ok user_id=%s job_id=%s", current_user.user_id, data.job_id)
    return api_success(
        data=data.model_dump(by_alias=True),
        message="Plan job created",
    )


@router.post("/execute")
async def execute_agent(
    request: Request,
    payload: ExecuteAgentRequest,
    current_user: User = Depends(require_verified_user),
    execute_service: ExecuteService = Depends(get_agent_execute_service),
):
    _log_agent_request(request, action="execute", user_id=current_user.user_id)
    data = await execute_service.enqueue_execute(user_id=current_user.user_id, request=payload)
    logger.info("agent.http execute ok user_id=%s job_id=%s", current_user.user_id, data.job_id)
    return api_success(
        data=data.model_dump(by_alias=True),
        message="Execute job created",
    )


@router.post("/cancel/{job_id}")
async def cancel_agent_job(
    request: Request,
    job_id: str,
    current_user: User = Depends(require_verified_user),
    execute_service: ExecuteService = Depends(get_agent_execute_service),
):
    _log_agent_request(request, action="cancel", user_id=current_user.user_id)
    raw = await execute_service.cancel_job(user_id=current_user.user_id, job_id=job_id)
    logger.info("agent.http cancel ok user_id=%s job_id=%s status=%s", current_user.user_id, job_id, raw.get("status"))
    data = CancelAgentResponse.model_validate(raw).model_dump(by_alias=True)
    return api_success(data=data, message="Job canceled")
