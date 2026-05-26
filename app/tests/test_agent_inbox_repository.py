from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fileflash.models import AgentInboxMessage
from fileflash.models.enums import AgentInboxKind, AgentInboxRole, AgentInboxStatus
from fileflash.repositories import AgentInboxMessageRepository


class InboxSession:
    def __init__(self) -> None:
        self.messages: list[AgentInboxMessage] = []
        self._next_id = 1
        self.commits = 0

    def add(self, msg: AgentInboxMessage) -> None:
        msg.inbox_message_id = self._next_id
        self._next_id += 1
        self.messages.append(msg)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def get(self, _model, inbox_message_id: int):  # noqa: ANN001
        for msg in self.messages:
            if msg.inbox_message_id == inbox_message_id:
                return msg
        return None

    async def scalar(self, _query):  # noqa: ANN001
        return None

    async def scalars(self, _query):  # noqa: ANN001
        controls = {
            AgentInboxKind.CONTROL_PAUSE,
            AgentInboxKind.CONTROL_RESUME,
            AgentInboxKind.CONTROL_APPROVE,
            AgentInboxKind.CONTROL_DENY,
            AgentInboxKind.CONTROL_SKIP,
            AgentInboxKind.CONTROL_CANCEL,
        }
        return [
            msg
            for msg in self.messages
            if msg.role == AgentInboxRole.USER
            and msg.kind in controls
            and msg.status is None
        ]


@pytest.mark.asyncio
async def test_create_ask_then_record_reply() -> None:
    session = InboxSession()
    repo = AgentInboxMessageRepository(session)  # type: ignore[arg-type]

    ask = await repo.create_ask(
        job_id=1,
        payload={"prompt": "choose", "schema": {"choice": ["A", "B"]}},
    )
    await session.commit()
    assert ask.status == AgentInboxStatus.WAITING
    assert ask.role == AgentInboxRole.AGENT
    assert ask.kind == AgentInboxKind.ASK

    reply = await repo.record_user_message(
        job_id=1,
        kind=AgentInboxKind.REPLY,
        payload={"value": "A"},
        reply_to_id=int(ask.inbox_message_id),
    )
    await session.commit()
    assert reply.role == AgentInboxRole.USER
    assert reply.reply_to_id == ask.inbox_message_id

    answered = await repo.mark_answered(
        inbox_message_id=int(ask.inbox_message_id),
        answered_at=datetime.now(UTC),
    )
    await session.commit()
    assert answered.status == AgentInboxStatus.ANSWERED
    assert answered.answered_at is not None


@pytest.mark.asyncio
async def test_pending_controls_excludes_consumed() -> None:
    session = InboxSession()
    repo = AgentInboxMessageRepository(session)  # type: ignore[arg-type]
    pause = await repo.record_user_message(
        job_id=1,
        kind=AgentInboxKind.CONTROL_PAUSE,
        payload={},
    )
    await session.commit()

    pending = await repo.list_pending_controls(job_id=1)
    assert [msg.inbox_message_id for msg in pending] == [pause.inbox_message_id]

    await repo.mark_dropped(inbox_message_id=int(pause.inbox_message_id))
    await session.commit()
    pending_after = await repo.list_pending_controls(job_id=1)
    assert pending_after == []
