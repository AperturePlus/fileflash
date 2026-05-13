from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from fileflash.models import BackgroundJob
from fileflash.services.background_jobs import BackgroundJobService, _build_queue_message


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


def test_build_queue_message_injects_job_id_when_missing_or_none():
    base_kwargs = dict(
        job_id=42,
        task_type="task.archive_extract",
        status="pending",
        result={},
        error_message=None,
        attempt=0,
        max_attempts=5,
        scheduled_at=datetime.now(UTC),
    )

    missing = BackgroundJob(payload={"targetFolderId": "root"}, requested_by=9, **base_kwargs)
    missing_message = _build_queue_message(missing)
    assert missing_message.payload["jobId"] == 42
    assert missing_message.payload["requestedBy"] == 9

    none_job_id = BackgroundJob(payload={"jobId": None, "targetFolderId": "root"}, requested_by=9, **base_kwargs)
    none_message = _build_queue_message(none_job_id)
    assert none_message.payload["jobId"] == 42

    keep_existing = BackgroundJob(payload={"jobId": 777, "targetFolderId": "root"}, requested_by=9, **base_kwargs)
    keep_message = _build_queue_message(keep_existing)
    assert keep_message.payload["jobId"] == 777


@pytest.mark.asyncio
async def test_enqueue_transcode_job_uses_object_storage_payload():
    session = DummySession()
    queue = SimpleNamespace(publish=AsyncMock(return_value="1-0"))
    service = BackgroundJobService(queue_publisher=queue)

    job = await service.enqueue_transcode_job(
        session,  # type: ignore[arg-type]
        source_bucket_name="fileflash",
        source_object_key="objects/u1/src.mp4",
        source_object_id=101,
        output_bucket_name="fileflash",
        output_object_key="optimized/transcode/v1/object-101/src-mp4-v1.mp4",
        file_id=999,
        requested_by=1,
        idempotency_key="object:101:transcode:mp4-v1",
    )

    payload = job.payload
    assert payload["sourceBucketName"] == "fileflash"
    assert payload["sourceObjectKey"] == "objects/u1/src.mp4"
    assert payload["sourceObjectId"] == 101
    assert payload["outputBucketName"] == "fileflash"
    assert payload["outputObjectKey"].endswith(".mp4")
    assert payload["fileId"] == 999
    assert payload["requestedBy"] == 1
