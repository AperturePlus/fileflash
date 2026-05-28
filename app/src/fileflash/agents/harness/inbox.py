from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.enums import AgentInboxKind, AgentInboxStatus
from ...repositories import AgentInboxMessageRepository
from .event_bus import AgentEventBus, AgentEventEnvelope

_INBOX_EVENT_TYPES: dict[AgentInboxKind, str] = {
    AgentInboxKind.REPLY: "agent.inbox.reply",
    AgentInboxKind.CONTROL_PAUSE: "agent.inbox.control",
    AgentInboxKind.CONTROL_RESUME: "agent.inbox.control",
    AgentInboxKind.CONTROL_APPROVE: "agent.inbox.control",
    AgentInboxKind.CONTROL_DENY: "agent.inbox.control",
    AgentInboxKind.CONTROL_SKIP: "agent.inbox.control",
    AgentInboxKind.CONTROL_CANCEL: "agent.inbox.control",
}


class AgentInbox:
    def __init__(self, *, db: AsyncSession, event_bus: AgentEventBus) -> None:
        self._db = db
        self._bus = event_bus
        self._repo = AgentInboxMessageRepository(db)

    async def handle(
        self,
        *,
        job_id: int,
        kind: AgentInboxKind,
        payload: dict[str, Any],
        reply_to_id: int | None = None,
    ):
        if kind == AgentInboxKind.REPLY:
            if reply_to_id is None:
                raise ValueError("reply requires reply_to_id")
            ask = await self._repo.get_ask(inbox_message_id=reply_to_id)
            if ask is None:
                raise ValueError(f"ask {reply_to_id} not found")
            if int(ask.job_id) != job_id:
                raise ValueError(f"ask {reply_to_id} belongs to a different job")
            if ask.status != AgentInboxStatus.WAITING:
                raise ValueError(f"ask {reply_to_id} is not waiting")

        msg = await self._repo.record_user_message(
            job_id=job_id,
            kind=kind,
            payload=payload,
            reply_to_id=reply_to_id,
        )
        event_type = _INBOX_EVENT_TYPES[kind]
        envelope_payload: dict[str, Any] = {
            "kind": kind.value,
            "messageId": str(msg.inbox_message_id),
        }
        if reply_to_id is not None:
            envelope_payload["replyTo"] = str(reply_to_id)
        if "value" in payload:
            envelope_payload["value"] = payload["value"]
        if "metadata" in payload:
            envelope_payload["metadata"] = payload["metadata"]
        await self._bus.publish(
            AgentEventEnvelope(
                job_id=job_id,
                event_type=event_type,
                payload=envelope_payload,
                emitted_at=datetime.now(UTC),
            )
        )
        return msg


__all__ = ["AgentInbox"]
