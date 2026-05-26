from __future__ import annotations

import json
from typing import Annotated, Any, get_args

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agents.harness.event_bus import AgentEventBus, AgentEventEnvelope
from ..agents.harness.inbox import AgentInbox
from ..core.deps import (
    get_agent_event_bus,
    get_agent_execute_service,
    get_agent_plan_service,
    get_current_user,
)
from ..core.errors import ApiError, api_success
from ..db.deps import get_db
from ..models import AgentActionLog, BackgroundJob
from ..models.enums import AgentInboxKind
from ..models.tables_identity import User
from ..schemas.agent import (
    AgentInboxMessageRequest,
    AgentInboxMessageResponse,
    AgentJobEvent,
    AgentJobEventType,
    ExecuteAgentRequest,
    PlanAgentRequest,
)
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


@router.get("/jobs/{job_id}/events")
async def stream_agent_job_events(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    event_bus: Annotated[AgentEventBus, Depends(get_agent_event_bus)],
):
    parsed_job_id = _parse_job_id(job_id)
    initial_events, initial_terminal = await _agent_job_events_for_job(
        db=db,
        job_id=parsed_job_id,
        user_id=int(current_user.user_id),
    )

    async def event_stream():
        seen: set[str] = set()
        for event in initial_events:
            seen.add(event.id)
            yield _format_sse_event(event)
        if initial_terminal:
            return
        async with event_bus.subscribe(job_id=parsed_job_id) as stream:
            while True:
                try:
                    envelope = await stream.next(timeout=30.0)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                event = _envelope_to_job_event(envelope)
                if event is None:
                    continue
                if event.id in seen:
                    continue
                seen.add(event.id)
                yield _format_sse_event(event)
                if event.type in {"job.succeeded", "job.failed", "job.canceled"}:
                    break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/jobs/{job_id}/messages")
async def post_agent_job_message(
    job_id: str,
    payload: AgentInboxMessageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    event_bus: Annotated[AgentEventBus, Depends(get_agent_event_bus)],
):
    parsed_job_id = _parse_job_id(job_id)
    job = await db.scalar(
        select(BackgroundJob)
        .where(
            and_(
                BackgroundJob.job_id == parsed_job_id,
                BackgroundJob.requested_by == current_user.user_id,
                BackgroundJob.task_type.in_(["agent.plan", "agent.execute"]),
            )
        )
    )
    if job is None:
        raise ApiError(status_code=404, code=404, message="Job not found")

    kind = AgentInboxKind(payload.kind)
    reply_to_id: int | None = None
    if payload.reply_to is not None:
        try:
            reply_to_id = int(payload.reply_to)
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message="Invalid replyTo") from exc

    inbox = AgentInbox(db=db, event_bus=event_bus)
    try:
        msg = await inbox.handle(
            job_id=parsed_job_id,
            kind=kind,
            payload=_inbox_payload_from_request(payload),
            reply_to_id=reply_to_id,
        )
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message=str(exc)) from exc
    await db.commit()

    data = AgentInboxMessageResponse(
        inbox_message_id=str(msg.inbox_message_id),
        kind=payload.kind,
        accepted_at=msg.created_at,
    )
    return api_success(data=data.model_dump(by_alias=True), message="Message accepted")


def _inbox_payload_from_request(req: AgentInboxMessageRequest) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if req.value is not None:
        body["value"] = req.value
    if req.metadata:
        body["metadata"] = req.metadata
    return body


def _parse_job_id(raw: str) -> int:
    try:
        parsed_job_id = int(raw)
    except ValueError as exc:
        raise ApiError(status_code=400, code=400, message="Invalid jobId") from exc
    if parsed_job_id <= 0:
        raise ApiError(status_code=400, code=400, message="Invalid jobId")
    return parsed_job_id


async def _agent_job_events_for_job(
    *,
    db: AsyncSession,
    job_id: int,
    user_id: int,
) -> tuple[list[AgentJobEvent], bool]:
    job = await db.scalar(
        select(BackgroundJob).where(
            and_(
                BackgroundJob.job_id == job_id,
                BackgroundJob.requested_by == user_id,
                BackgroundJob.task_type.in_(["agent.plan", "agent.execute"]),
            )
        )
    )
    if job is None:
        raise ApiError(status_code=404, code=404, message="Job not found")

    terminal = str(job.status) in {"succeeded", "failed", "canceled"}
    events: list[AgentJobEvent] = []
    if job.task_type == "agent.plan" and job.status == "succeeded" and job.result:
        events.append(_plan_ready_event(job))
        events.append(_job_status_event(job))
    elif job.task_type != "agent.execute" or not terminal:
        events.append(_job_status_event(job))

    if job.task_type == "agent.execute":
        action_logs = list(
            await db.scalars(
                select(AgentActionLog)
                .where(AgentActionLog.job_id == job_id)
                .order_by(AgentActionLog.step_no.asc())
            )
        )
        for action_log in action_logs:
            events.extend(_tool_events(job=job, action_log=action_log))
        if terminal:
            events.append(_job_status_event(job))

    return events, terminal


def _job_status_event(job: BackgroundJob) -> AgentJobEvent:
    status = str(job.status)
    event_type = {
        "pending": "job.queued",
        "running": "job.running",
        "succeeded": "job.succeeded",
        "failed": "job.failed",
        "canceled": "job.canceled",
    }.get(status, "job.running")
    timestamp = job.updated_at or job.created_at
    return AgentJobEvent(
        id=f"{job.job_id}:job:{status}:{timestamp.isoformat()}",
        job_id=str(job.job_id),
        task_type=str(job.task_type),
        type=event_type,  # type: ignore[arg-type]
        status=status,
        agent_phase=job.agent_phase,
        message=_job_status_message(job),
        data=_job_status_data(job),
        timestamp=timestamp,
    )


def _plan_ready_event(job: BackgroundJob) -> AgentJobEvent:
    timestamp = job.finished_at or job.updated_at or job.created_at
    return AgentJobEvent(
        id=f"{job.job_id}:plan-ready",
        job_id=str(job.job_id),
        task_type=str(job.task_type),
        type="plan.ready",
        status=str(job.status),
        agent_phase=job.agent_phase,
        message="计划已生成。",
        data={"result": dict(job.result or {})},
        timestamp=timestamp,
    )


def _tool_events(*, job: BackgroundJob, action_log: AgentActionLog) -> list[AgentJobEvent]:
    events = [
        AgentJobEvent(
            id=f"{job.job_id}:tool:{action_log.action_log_id}:started",
            job_id=str(job.job_id),
            task_type=str(job.task_type),
            type="tool.started",
            status=str(job.status),
            agent_phase=job.agent_phase,
            message=_tool_started_message(action_log),
            data=_tool_event_data(action_log, include_output=False),
            timestamp=action_log.started_at,
        )
    ]
    if action_log.status in {"succeeded", "failed"} and action_log.finished_at is not None:
        events.append(
            AgentJobEvent(
                id=f"{job.job_id}:tool:{action_log.action_log_id}:{action_log.status}",
                job_id=str(job.job_id),
                task_type=str(job.task_type),
                type="tool.succeeded" if action_log.status == "succeeded" else "tool.failed",
                status=str(job.status),
                agent_phase=job.agent_phase,
                message=_tool_finished_message(action_log),
                data=_tool_event_data(action_log, include_output=True),
                timestamp=action_log.finished_at,
            )
        )
    return events


def _job_status_message(job: BackgroundJob) -> str:
    status = str(job.status)
    if status == "pending":
        return "任务已排队。"
    if status == "running":
        return "正在规划任务。" if job.task_type == "agent.plan" else "正在执行计划。"
    if status == "succeeded":
        result = dict(job.result or {})
        answer = result.get("answer")
        if isinstance(answer, str) and answer.strip():
            return "答案已生成。"
        return "任务已完成。"
    if status == "failed":
        return str(job.error_message or "任务失败。")
    if status == "canceled":
        return "任务已取消。"
    return "任务状态已更新。"


def _job_status_data(job: BackgroundJob) -> dict[str, object]:
    data: dict[str, object] = {}
    if job.status in {"succeeded", "failed", "canceled"}:
        data["result"] = dict(job.result or {})
    if job.error_message:
        data["errorMessage"] = job.error_message
    return data


def _tool_started_message(action_log: AgentActionLog) -> str:
    if action_log.tool_name == "drive.countFiles":
        inputs = dict(action_log.inputs_json or {})
        search = str(inputs.get("search") or "").strip()
        category = str(inputs.get("category") or "").strip()
        target = "视频文件" if category == "video" else "文件"
        if search:
            return f"正在读取名称包含“{search}”的{target}数量。"
        return f"正在读取{target}数量。"
    return f"正在调用 {action_log.tool_name}。"


def _tool_finished_message(action_log: AgentActionLog) -> str:
    if action_log.status == "failed":
        return str(action_log.error_message or f"{action_log.tool_name} 调用失败。")
    if action_log.tool_name == "drive.countFiles":
        outputs = dict(action_log.outputs_json or {})
        total_items = int(outputs.get("totalItems") or 0)
        return f"读取完成，匹配 {total_items} 个文件。"
    return f"{action_log.tool_name} 已完成。"


def _tool_event_data(action_log: AgentActionLog, *, include_output: bool) -> dict[str, object]:
    data: dict[str, object] = {
        "step": int(action_log.step_no),
        "tool": str(action_log.tool_name),
        "input": dict(action_log.inputs_json or {}),
    }
    if include_output:
        data["output"] = dict(action_log.outputs_json or {})
        if action_log.duration_ms is not None:
            data["durationMs"] = int(action_log.duration_ms)
    if action_log.error_message:
        data["errorMessage"] = action_log.error_message
    return data


def _envelope_to_job_event(env: AgentEventEnvelope) -> AgentJobEvent | None:
    if env.event_type.startswith("agent.inbox."):
        return None
    if env.event_type not in get_args(AgentJobEventType):
        return None
    payload = dict(env.payload or {})
    data = payload.get("data")
    return AgentJobEvent(
        id=env.event_id or f"{env.job_id}:{env.event_type}:{env.emitted_at.isoformat()}",
        job_id=str(env.job_id),
        task_type=str(payload.get("taskType") or "agent.execute"),
        type=env.event_type,  # type: ignore[arg-type]
        status=str(payload.get("status") or "running"),
        agent_phase=payload.get("agentPhase"),
        message=str(payload.get("message") or ""),
        data=dict(data) if isinstance(data, dict) else payload,
        timestamp=env.emitted_at,
    )


def _format_sse_event(event: AgentJobEvent) -> str:
    payload = event.model_dump(by_alias=True, mode="json")
    return (
        f"id: {event.id}\n"
        f"event: {event.type}\n"
        f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"
    )


__all__ = ["router"]
