from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fileflash.agents.harness.event_bus import AgentEventEnvelope, InMemoryAgentEventBus


@pytest.mark.asyncio
async def test_subscriber_receives_published_event() -> None:
    bus = InMemoryAgentEventBus()
    envelope = AgentEventEnvelope(
        job_id=42,
        event_type="agent.ask",
        payload={"prompt": "choose"},
        emitted_at=datetime.now(UTC),
    )

    async with bus.subscribe(job_id=42) as stream:
        await bus.publish(envelope)
        received = await stream.next(timeout=1.0)

    assert received == envelope


@pytest.mark.asyncio
async def test_only_subscribers_of_same_job_receive() -> None:
    bus = InMemoryAgentEventBus()
    own = AgentEventEnvelope(
        job_id=1,
        event_type="job.running",
        payload={},
        emitted_at=datetime.now(UTC),
    )
    other = AgentEventEnvelope(
        job_id=2,
        event_type="job.running",
        payload={},
        emitted_at=datetime.now(UTC),
    )

    async with bus.subscribe(job_id=1) as stream:
        await bus.publish(other)
        await bus.publish(own)
        first = await stream.next(timeout=1.0)

    assert first == own


@pytest.mark.asyncio
async def test_empty_subscriber_times_out() -> None:
    bus = InMemoryAgentEventBus()
    async with bus.subscribe(job_id=7) as stream:
        with pytest.raises(TimeoutError):
            await stream.next(timeout=0.1)


def test_event_envelope_json_serializes_nested_datetime_payload() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    envelope = AgentEventEnvelope(
        job_id=9,
        event_type="job.succeeded",
        payload={
            "data": {
                "result": {
                    "finishedAt": now,
                    "steps": [{"completedAt": now}],
                }
            }
        },
        emitted_at=now,
        event_id="evt-1",
    )

    decoded = AgentEventEnvelope.from_json(envelope.to_json())

    assert decoded.job_id == envelope.job_id
    assert decoded.event_type == envelope.event_type
    assert decoded.event_id == "evt-1"
    assert decoded.payload["data"]["result"]["finishedAt"] == now.isoformat()
    assert decoded.payload["data"]["result"]["steps"][0]["completedAt"] == now.isoformat()
