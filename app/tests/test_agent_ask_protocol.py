from __future__ import annotations

import asyncio

import pytest
from test_agent_inbox_repository import InboxSession

from fileflash.agents.harness.ask import AskProtocol, AskTimedOut
from fileflash.agents.harness.event_bus import InMemoryAgentEventBus
from fileflash.agents.harness.inbox import AgentInbox
from fileflash.models.enums import AgentInboxKind, AgentInboxStatus


@pytest.mark.asyncio
async def test_ask_returns_when_reply_arrives() -> None:
    session = InboxSession()
    bus = InMemoryAgentEventBus()
    inbox = AgentInbox(db=session, event_bus=bus)  # type: ignore[arg-type]
    protocol = AskProtocol(db=session, event_bus=bus, job_id=1)  # type: ignore[arg-type]

    await protocol.start()
    try:
        async def reply_later() -> None:
            for _ in range(20):
                asks = [msg for msg in session.messages if msg.kind == AgentInboxKind.ASK]
                if asks:
                    ask = asks[-1]
                    await inbox.handle(
                        job_id=1,
                        kind=AgentInboxKind.REPLY,
                        payload={"value": "A"},
                        reply_to_id=int(ask.inbox_message_id),
                    )
                    await session.commit()
                    return
                await asyncio.sleep(0.01)
            raise AssertionError("ask message was not created")

        replier = asyncio.create_task(reply_later())
        result = await protocol.ask(
            prompt="choose",
            schema={"choice": ["A", "B"]},
            timeout_sec=2.0,
        )
        await replier
    finally:
        await protocol.aclose()

    assert result == "A"


@pytest.mark.asyncio
async def test_ask_times_out() -> None:
    session = InboxSession()
    bus = InMemoryAgentEventBus()
    protocol = AskProtocol(db=session, event_bus=bus, job_id=1)  # type: ignore[arg-type]

    await protocol.start()
    try:
        with pytest.raises(AskTimedOut):
            await protocol.ask(prompt="?", schema={}, timeout_sec=0.1)
    finally:
        await protocol.aclose()

    asks = [msg for msg in session.messages if msg.kind == AgentInboxKind.ASK]
    assert asks
    assert asks[-1].status == AgentInboxStatus.TIMED_OUT
