from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import AgentInboxMessage
from ...models.enums import AgentInboxKind, AgentInboxRole, AgentInboxStatus

_CONTROL_KINDS = frozenset(
    {
        AgentInboxKind.CONTROL_PAUSE,
        AgentInboxKind.CONTROL_RESUME,
        AgentInboxKind.CONTROL_APPROVE,
        AgentInboxKind.CONTROL_DENY,
        AgentInboxKind.CONTROL_SKIP,
        AgentInboxKind.CONTROL_CANCEL,
    }
)


class AgentInboxMessageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_ask(
        self,
        *,
        job_id: int,
        payload: dict[str, Any],
    ) -> AgentInboxMessage:
        msg = AgentInboxMessage(
            job_id=job_id,
            role=AgentInboxRole.AGENT,
            kind=AgentInboxKind.ASK,
            payload_json=payload,
            status=AgentInboxStatus.WAITING,
            created_at=datetime.now(UTC),
        )
        self._db.add(msg)
        await self._db.flush()
        return msg

    async def record_user_message(
        self,
        *,
        job_id: int,
        kind: AgentInboxKind,
        payload: dict[str, Any],
        reply_to_id: int | None = None,
    ) -> AgentInboxMessage:
        msg = AgentInboxMessage(
            job_id=job_id,
            role=AgentInboxRole.USER,
            kind=kind,
            payload_json=payload,
            reply_to_id=reply_to_id,
            status=None,
            created_at=datetime.now(UTC),
        )
        self._db.add(msg)
        await self._db.flush()
        return msg

    async def mark_answered(
        self,
        *,
        inbox_message_id: int,
        answered_at: datetime,
    ) -> AgentInboxMessage:
        msg = await self._db.get(AgentInboxMessage, inbox_message_id)
        if msg is None:
            raise ValueError(f"AgentInboxMessage {inbox_message_id} not found")
        msg.status = AgentInboxStatus.ANSWERED
        msg.answered_at = answered_at
        await self._db.flush()
        return msg

    async def mark_timed_out(
        self,
        *,
        inbox_message_id: int,
        answered_at: datetime,
    ) -> AgentInboxMessage:
        msg = await self._db.get(AgentInboxMessage, inbox_message_id)
        if msg is None:
            raise ValueError(f"AgentInboxMessage {inbox_message_id} not found")
        msg.status = AgentInboxStatus.TIMED_OUT
        msg.answered_at = answered_at
        await self._db.flush()
        return msg

    async def mark_dropped(self, *, inbox_message_id: int) -> None:
        msg = await self._db.get(AgentInboxMessage, inbox_message_id)
        if msg is None:
            return
        if msg.kind in _CONTROL_KINDS:
            msg.status = AgentInboxStatus.DROPPED
            msg.answered_at = datetime.now(UTC)
        await self._db.flush()

    async def get_ask(self, *, inbox_message_id: int) -> AgentInboxMessage | None:
        msg = await self._db.get(AgentInboxMessage, inbox_message_id)
        if msg is None or msg.kind != AgentInboxKind.ASK:
            return None
        return msg

    async def get_reply_for(self, *, ask_id: int) -> AgentInboxMessage | None:
        return await self._db.scalar(
            select(AgentInboxMessage).where(
                and_(
                    AgentInboxMessage.reply_to_id == ask_id,
                    AgentInboxMessage.kind == AgentInboxKind.REPLY,
                )
            )
        )

    async def list_pending_controls(self, *, job_id: int) -> list[AgentInboxMessage]:
        rows = await self._db.scalars(
            select(AgentInboxMessage)
            .where(
                and_(
                    AgentInboxMessage.job_id == job_id,
                    AgentInboxMessage.role == AgentInboxRole.USER,
                    AgentInboxMessage.kind.in_(list(_CONTROL_KINDS)),
                    AgentInboxMessage.status.is_(None),
                )
            )
            .order_by(AgentInboxMessage.created_at.asc())
        )
        return list(rows)


__all__ = ["AgentInboxMessageRepository"]
