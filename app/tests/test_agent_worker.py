from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from fileflash.agents.harness.event_bus import AgentEventEnvelope
from fileflash.agents.worker import AgentWorkerConsumer
from fileflash.models import BackgroundJob


class _AsyncContextManager:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, exc_type, exc, tb):
        return None


class DummySession:
    def __init__(self, job: BackgroundJob):
        self._job = job

    def begin(self):
        return _AsyncContextManager(SimpleNamespace())

    async def scalar(self, _query):  # noqa: ANN001
        return self._job


class CaptureBus:
    def __init__(self) -> None:
        self.events: list[AgentEventEnvelope] = []

    async def publish(self, envelope: AgentEventEnvelope) -> None:
        self.events.append(envelope)


class FailingBus:
    async def publish(self, envelope: AgentEventEnvelope) -> None:  # noqa: ARG002
        raise RuntimeError("publish unavailable")


def _job(*, status: str, cancel_requested_at: datetime | None) -> BackgroundJob:
    now = datetime.now(UTC)
    return BackgroundJob(
        job_id=65,
        task_type="agent.plan",
        status=status,
        payload={},
        result={},
        requested_by=7,
        cancel_requested_at=cancel_requested_at,
        scheduled_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_mark_succeeded_does_not_override_canceled_job(monkeypatch: pytest.MonkeyPatch):
    canceled_at = datetime.now(UTC)
    job = _job(status="canceled", cancel_requested_at=canceled_at)
    session = DummySession(job)
    consumer = AgentWorkerConsumer(
        queue=SimpleNamespace(),
        session_factory=lambda: _AsyncContextManager(session),  # type: ignore[arg-type]
    )
    monkeypatch.setattr("fileflash.agents.worker.apply_local_lock_timeout", AsyncMock(return_value=None))

    await consumer._mark_succeeded(job_id=65, result={"summary": "ok"}, phase="completed")

    assert job.status == "canceled"
    assert job.cancel_requested_at == canceled_at
    assert job.result == {}


@pytest.mark.asyncio
async def test_mark_failed_does_not_override_job_with_cancel_request(monkeypatch: pytest.MonkeyPatch):
    canceled_at = datetime.now(UTC)
    job = _job(status="running", cancel_requested_at=canceled_at)
    session = DummySession(job)
    consumer = AgentWorkerConsumer(
        queue=SimpleNamespace(),
        session_factory=lambda: _AsyncContextManager(session),  # type: ignore[arg-type]
    )
    monkeypatch.setattr("fileflash.agents.worker.apply_local_lock_timeout", AsyncMock(return_value=None))

    await consumer._mark_failed(job_id=65, error=RuntimeError("boom"))

    assert job.status == "running"
    assert job.cancel_requested_at == canceled_at
    assert job.error_message is None


@pytest.mark.asyncio
async def test_mark_succeeded_publishes_terminal_event(monkeypatch: pytest.MonkeyPatch):
    job = _job(status="running", cancel_requested_at=None)
    session = DummySession(job)
    bus = CaptureBus()
    consumer = AgentWorkerConsumer(
        queue=SimpleNamespace(),
        session_factory=lambda: _AsyncContextManager(session),  # type: ignore[arg-type]
        event_bus=bus,
    )
    monkeypatch.setattr("fileflash.agents.worker.apply_local_lock_timeout", AsyncMock(return_value=None))

    finished_at = datetime.now(UTC).replace(microsecond=0)
    await consumer._mark_succeeded(
        job_id=65,
        result={"summary": "ok", "finishedAt": finished_at},
        phase="completed",
    )

    assert [event.event_type for event in bus.events] == ["job.succeeded"]
    assert bus.events[0].payload["status"] == "succeeded"
    assert bus.events[0].payload["data"]["result"]["finishedAt"] == finished_at.isoformat()
    assert job.result["finishedAt"] == finished_at.isoformat()


@pytest.mark.asyncio
async def test_mark_succeeded_ignores_publish_failures(monkeypatch: pytest.MonkeyPatch):
    job = _job(status="running", cancel_requested_at=None)
    session = DummySession(job)
    consumer = AgentWorkerConsumer(
        queue=SimpleNamespace(),
        session_factory=lambda: _AsyncContextManager(session),  # type: ignore[arg-type]
        event_bus=FailingBus(),
    )
    monkeypatch.setattr("fileflash.agents.worker.apply_local_lock_timeout", AsyncMock(return_value=None))

    await consumer._mark_succeeded(job_id=65, result={"summary": "ok"}, phase="completed")

    assert job.status == "succeeded"
    assert job.result["summary"] == "ok"
