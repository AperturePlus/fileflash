from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...agents.harness.event_bus import AgentEventBus
from ...agents.harness.inbox import AgentInbox
from ...core.errors import ApiError
from ...models import AgentChatSession, AgentInboxMessage, BackgroundJob
from ...models.enums import AgentInboxKind, AgentInboxStatus
from ...repositories import (
    AgentActionLogRepository,
    AgentChatSessionRepository,
    AgentWorkSessionRepository,
)
from ...schemas.agent import (
    AgentChatMessage,
    AgentChatSessionDetail,
    AgentChatSessionItem,
    AttachAgentJobsResponse,
    CreateAgentChatSessionRequest,
    PatchAgentChatSessionRequest,
)


class SessionService:
    def __init__(
        self,
        *,
        db: AsyncSession,
        event_bus: AgentEventBus,
        chat_sessions: AgentChatSessionRepository,
        action_logs: AgentActionLogRepository,
        work_sessions: AgentWorkSessionRepository,
    ) -> None:
        self.db = db
        self.event_bus = event_bus
        self.chat_sessions = chat_sessions
        self.action_logs = action_logs
        self.work_sessions = work_sessions

    async def create_chat_session(
        self,
        *,
        user_id: int,
        payload: CreateAgentChatSessionRequest,
    ) -> AgentChatSessionItem:
        entity = await self.chat_sessions.create(
            user_id=user_id,
            title=payload.title or "New session",
        )
        await self.db.commit()
        return _session_item(entity)

    async def list_chat_sessions(self, *, user_id: int) -> list[AgentChatSessionItem]:
        rows = await self.chat_sessions.list_active(user_id=user_id)
        return [_session_item(row) for row in rows]

    async def get_chat_session(self, *, user_id: int, chat_session_id: int) -> AgentChatSessionDetail:
        entity = await self.chat_sessions.get_active(
            user_id=user_id,
            chat_session_id=chat_session_id,
        )
        if entity is None:
            raise ApiError(status_code=404, code=404, message="Agent chat session not found")
        jobs = await self.chat_sessions.list_jobs(chat_session_id=chat_session_id)
        pending_asks = await self._pending_asks_by_job(job_ids=[int(job.job_id) for job in jobs])
        item = _session_item(entity)
        return AgentChatSessionDetail(
            **item.model_dump(),
            messages=_messages_from_jobs(jobs=jobs, pending_asks=pending_asks),
        )

    async def patch_chat_session(
        self,
        *,
        user_id: int,
        chat_session_id: int,
        payload: PatchAgentChatSessionRequest,
    ) -> AgentChatSessionItem:
        entity = await self.chat_sessions.get_active(
            user_id=user_id,
            chat_session_id=chat_session_id,
        )
        if entity is None:
            raise ApiError(status_code=404, code=404, message="Agent chat session not found")
        updated = await self.chat_sessions.update(
            entity=entity,
            title=payload.title,
            archived=payload.archived,
        )
        await self.db.commit()
        return _session_item(updated)

    async def attach_jobs(
        self,
        *,
        user_id: int,
        chat_session_id: int,
        job_ids: list[int],
    ) -> AttachAgentJobsResponse:
        entity = await self.chat_sessions.get_active(
            user_id=user_id,
            chat_session_id=chat_session_id,
        )
        if entity is None:
            raise ApiError(status_code=404, code=404, message="Agent chat session not found")
        count = await self.chat_sessions.attach_jobs(
            chat_session_id=chat_session_id,
            user_id=user_id,
            job_ids=job_ids,
        )
        entity.updated_at = datetime.now(UTC)
        await self.db.commit()
        return AttachAgentJobsResponse(attached_count=count)

    async def delete_chat_session(self, *, user_id: int, chat_session_id: int) -> AgentChatSessionItem:
        entity = await self.chat_sessions.get_active(
            user_id=user_id,
            chat_session_id=chat_session_id,
            for_update=True,
        )
        if entity is None:
            raise ApiError(status_code=404, code=404, message="Agent chat session not found")
        now = datetime.now(UTC)
        entity.deleted_at = now
        entity.updated_at = now

        jobs = await self.chat_sessions.list_jobs(chat_session_id=chat_session_id)
        inbox = AgentInbox(db=self.db, event_bus=self.event_bus)
        for job in jobs:
            job.deleted_at = now
            job.updated_at = now
            if _is_unfinished_job(job):
                job.cancel_requested_at = job.cancel_requested_at or now
                await inbox.handle(
                    job_id=int(job.job_id),
                    kind=AgentInboxKind.CONTROL_CANCEL,
                    payload={"metadata": {"source": "chatSession.delete"}},
                )
        await self.db.commit()
        return _session_item(entity)

    async def _pending_asks_by_job(self, *, job_ids: list[int]) -> dict[int, dict[str, Any]]:
        if not job_ids:
            return {}
        rows = await self.db.scalars(
            select(AgentInboxMessage).where(
                and_(
                    AgentInboxMessage.job_id.in_(job_ids),
                    AgentInboxMessage.kind == AgentInboxKind.ASK,
                    AgentInboxMessage.status == AgentInboxStatus.WAITING,
                )
            )
        )
        out: dict[int, dict[str, Any]] = {}
        for msg in rows:
            payload = dict(msg.payload_json or {})
            out[int(msg.job_id)] = {
                "messageId": str(msg.inbox_message_id),
                "prompt": str(payload.get("prompt") or ""),
                "schema": payload.get("schema") if isinstance(payload.get("schema"), dict) else {},
                "timeoutSec": int(float(payload.get("timeoutSec") or 0)),
                "askedAt": msg.created_at.isoformat(),
            }
        return out


def _session_item(entity: AgentChatSession) -> AgentChatSessionItem:
    return AgentChatSessionItem(
        chat_session_id=str(entity.chat_session_id),
        title=entity.title,
        archived=bool(entity.archived),
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _is_unfinished_job(job: BackgroundJob) -> bool:
    return str(job.status) in {"pending", "queued", "running", "retrying", "paused"}


def _messages_from_jobs(
    *,
    jobs: list[BackgroundJob],
    pending_asks: dict[int, dict[str, Any]],
) -> list[AgentChatMessage]:
    plan_messages: dict[str, AgentChatMessage] = {}
    messages: list[AgentChatMessage] = []

    for job in jobs:
        if job.task_type != "agent.plan":
            continue
        payload = dict(job.payload or {})
        result = dict(job.result or {})
        user_msg = AgentChatMessage(
            id=f"job-{job.job_id}:user",
            role="user",
            content=str(payload.get("input") or ""),
            status="succeeded",
            timestamp=job.created_at,
        )
        plan_result = result if job.status == "succeeded" and result else None
        agent_msg = AgentChatMessage(
            id=f"job-{job.job_id}:agent",
            role="agent",
            content="",
            status=_message_status(job),
            plan_job_id=str(job.job_id),
            plan_hash=str(plan_result.get("planHash") or "") if plan_result else None,
            plan_result=plan_result,
            error_message=job.error_message,
            timestamp=job.created_at,
            pending_ask=pending_asks.get(int(job.job_id)),
        )
        if agent_msg.pending_ask:
            agent_msg.status = "waiting_for_user"
        messages.extend([user_msg, agent_msg])
        plan_messages[str(job.job_id)] = agent_msg

    for job in jobs:
        if job.task_type != "agent.execute":
            continue
        payload = dict(job.payload or {})
        plan_job_id = str(payload.get("planJobId") or "")
        agent_msg = plan_messages.get(plan_job_id)
        if agent_msg is None:
            agent_msg = AgentChatMessage(
                id=f"job-{job.job_id}:agent",
                role="agent",
                content="",
                status=_message_status(job),
                timestamp=job.created_at,
            )
            messages.append(agent_msg)
        agent_msg.execute_job_id = str(job.job_id)
        if job.status == "succeeded" and job.result:
            agent_msg.execute_result = dict(job.result or {})
        agent_msg.status = _message_status(job)
        if job.error_message:
            agent_msg.error_message = job.error_message
        if pending_asks.get(int(job.job_id)):
            agent_msg.pending_ask = pending_asks[int(job.job_id)]
            agent_msg.status = "waiting_for_user"

    return messages


def _message_status(job: BackgroundJob) -> str:
    status = str(job.status or "")
    if status in {"pending", "running", "succeeded", "failed", "canceled", "paused"}:
        return status
    return "running"
