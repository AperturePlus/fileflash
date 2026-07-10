from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..db.transaction import is_unique_violation_error
from ..models import BackgroundJob
from ..workers.contracts import WorkerJobMessage
from .job_queue import JobQueuePublisher


class BackgroundJobService:
    def __init__(self, *, queue_publisher: JobQueuePublisher | None = None) -> None:
        self._queue_publisher = queue_publisher

    async def enqueue(
        self,
        db: AsyncSession,
        *,
        task_type: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
        requested_by: int | None = None,
        max_attempts: int = 5,
        priority: int = 100,
        agent_phase: str | None = None,
        chat_session_id: int | None = None,
    ) -> BackgroundJob:
        now = datetime.now(UTC)
        normalized_payload = jsonable_encoder(payload)
        job = BackgroundJob(
            task_type=task_type,
            status="pending",
            payload=normalized_payload,
            result={},
            error_message=None,
            attempt=0,
            max_attempts=max_attempts,
            scheduled_at=now,
            trace_id=str(uuid.uuid4()),
            idempotency_key=idempotency_key,
            agent_phase=agent_phase,
            chat_session_id=chat_session_id,
            requested_by=requested_by,
            priority=priority,
        )
        db.add(job)
        try:
            await db.flush()
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            if idempotency_key and is_unique_violation_error(exc):
                existing = await db.scalar(
                    select(BackgroundJob).where(BackgroundJob.idempotency_key == idempotency_key)
                )
                if existing is not None:
                    return existing
            raise

        if self._queue_publisher is None:
            job.status = "failed"
            job.error_message = "Job queue unavailable"
            job.finished_at = now
            job.updated_at = now
            await db.commit()
            raise ApiError(
                status_code=503,
                code=503,
                message="Job queue unavailable",
                data={"jobId": str(job.job_id)},
            )

        try:
            await self._queue_publisher.publish(_build_queue_message(job))
        except Exception as exc:
            job.status = "failed"
            job.error_message = f"Publish failed: {type(exc).__name__}: {exc}"[:2000]
            job.finished_at = now
            job.updated_at = now
            await db.commit()
            raise ApiError(
                status_code=503,
                code=503,
                message="Job queue unavailable",
                data={"jobId": str(job.job_id)},
            ) from exc
        return job

    async def enqueue_scan_job(
        self,
        db: AsyncSession,
        *,
        local_path: str,
        object_id: int | None = None,
        requested_by: int | None = None,
        idempotency_key: str | None = None,
    ) -> BackgroundJob:
        payload: dict[str, Any] = {"localPath": local_path}
        if object_id is not None:
            payload["objectId"] = object_id
        return await self.enqueue(
            db,
            task_type="task.scan",
            payload=payload,
            idempotency_key=idempotency_key,
            requested_by=requested_by,
        )

    async def enqueue_transcode_job(
        self,
        db: AsyncSession,
        *,
        source_bucket_name: str,
        source_object_key: str,
        source_object_id: int,
        output_bucket_name: str,
        output_object_key: str,
        file_id: int | None = None,
        requested_by: int | None = None,
        idempotency_key: str | None = None,
    ) -> BackgroundJob:
        payload: dict[str, Any] = {
            "sourceBucketName": source_bucket_name,
            "sourceObjectKey": source_object_key,
            "sourceObjectId": source_object_id,
            "outputBucketName": output_bucket_name,
            "outputObjectKey": output_object_key,
        }
        if file_id is not None:
            payload["fileId"] = file_id
        if requested_by is not None:
            payload["requestedBy"] = requested_by
        return await self.enqueue(
            db,
            task_type="task.transcode",
            payload=payload,
            idempotency_key=idempotency_key,
            requested_by=requested_by,
        )


def _build_queue_message(job: BackgroundJob) -> WorkerJobMessage:
    payload = dict(job.payload or {})
    if payload.get("jobId") in (None, ""):
        payload["jobId"] = job.job_id
    if job.requested_by is not None:
        payload.setdefault("requestedBy", job.requested_by)
    return WorkerJobMessage(
        version=1,
        message_id=f"job-{job.job_id}-attempt-{job.attempt}",
        job_id=job.job_id,
        task_type=job.task_type,
        idempotency_key=job.idempotency_key,
        attempt=job.attempt,
        max_attempts=job.max_attempts,
        trace_id=job.trace_id or f"job-{job.job_id}",
        requested_by=str(job.requested_by) if job.requested_by is not None else None,
        payload=payload,
    )
