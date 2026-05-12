from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from src.models import BackgroundJob
from src.services.background_jobs import BackgroundJobService


class _PgUniqueViolation(Exception):
    sqlstate = "23505"


class DummySession:
    def __init__(self) -> None:
        self.scalar = AsyncMock()
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)


@pytest.mark.asyncio
async def test_enqueue_returns_existing_job_for_same_idempotency_key_any_status():
    session = DummySession()
    existing = BackgroundJob(
        job_id=99,
        task_type="task.scan",
        status="succeeded",
        payload={},
        result={},
        error_message=None,
        attempt=1,
        max_attempts=5,
        scheduled_at=datetime.now(UTC),
    )
    session.scalar.return_value = existing
    session.flush.side_effect = IntegrityError("insert", {}, _PgUniqueViolation())
    queue = SimpleNamespace(publish=AsyncMock())
    service = BackgroundJobService(queue_publisher=queue)

    job = await service.enqueue(
        session,  # type: ignore[arg-type]
        task_type="task.scan",
        payload={"localPath": "/tmp/a"},
        idempotency_key="idem-1",
        requested_by=1,
    )

    assert job is existing
    assert len(session.added) == 1
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    queue.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_enqueue_recovers_from_unique_conflict_and_returns_existing_job():
    session = DummySession()
    second_existing = BackgroundJob(
        job_id=100,
        task_type="task.scan",
        status="pending",
        payload={},
        result={},
        error_message=None,
        attempt=0,
        max_attempts=5,
        scheduled_at=datetime.now(UTC),
    )
    session.scalar.return_value = second_existing
    session.flush.side_effect = IntegrityError("insert", {}, _PgUniqueViolation())
    queue = SimpleNamespace(publish=AsyncMock())
    service = BackgroundJobService(queue_publisher=queue)

    job = await service.enqueue(
        session,  # type: ignore[arg-type]
        task_type="task.scan",
        payload={"localPath": "/tmp/a"},
        idempotency_key="idem-2",
        requested_by=1,
    )

    assert job is second_existing
    session.rollback.assert_awaited_once()
    queue.publish.assert_not_awaited()
