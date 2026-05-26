from __future__ import annotations

import pytest
from test_agent_inbox_repository import InboxSession

from fileflash.agents.harness.event_bus import InMemoryAgentEventBus
from fileflash.agents.harness.inbox import AgentInbox
from fileflash.models import AgentInboxMessage
from fileflash.models.enums import AgentInboxKind
from fileflash.repositories import AgentInboxMessageRepository


@pytest.mark.asyncio
async def test_handle_reply_persists_and_publishes() -> None:
    session = InboxSession()
    repo = AgentInboxMessageRepository(session)  # type: ignore[arg-type]
    ask = await repo.create_ask(job_id=1, payload={"prompt": "?"})
    await session.commit()

    bus = InMemoryAgentEventBus()
    inbox = AgentInbox(db=session, event_bus=bus)  # type: ignore[arg-type]

    async with bus.subscribe(job_id=1) as stream:
        msg = await inbox.handle(
            job_id=1,
            kind=AgentInboxKind.REPLY,
            payload={"value": "yes"},
            reply_to_id=int(ask.inbox_message_id),
        )
        await session.commit()
        event = await stream.next(timeout=1.0)

    assert isinstance(msg, AgentInboxMessage)
    assert msg.kind == AgentInboxKind.REPLY
    assert event.event_type == "agent.inbox.reply"
    assert event.payload["replyTo"] == str(ask.inbox_message_id)
    assert event.payload["value"] == "yes"


@pytest.mark.asyncio
async def test_reply_with_unknown_ask_raises() -> None:
    session = InboxSession()
    bus = InMemoryAgentEventBus()
    inbox = AgentInbox(db=session, event_bus=bus)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        await inbox.handle(
            job_id=1,
            kind=AgentInboxKind.REPLY,
            payload={"value": "yes"},
            reply_to_id=999999,
        )
