from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

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
