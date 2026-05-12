from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.transaction import apply_local_lock_timeout
from ..models import BackgroundJob
from .contracts import WorkerJobMessage


async def mark_job_running(
    db: AsyncSession,
    *,
    job_id: int,
    default_max_attempts: int,
) -> WorkerJobMessage | None:
    now = datetime.now(UTC)
    job = await _load_job_for_update(db, job_id=job_id)
    if job is None:
        return None

    if job.status in ("succeeded", "failed", "canceled"):
        return None
    if job.max_attempts <= 0:
        job.max_attempts = default_max_attempts
    if not job.trace_id:
        job.trace_id = f"job-{job.job_id}"

    job.status = "running"
    job.started_at = now
    job.updated_at = now
    job.error_message = None

    return WorkerJobMessage(
        version=1,
        message_id=f"job-{job.job_id}-attempt-{job.attempt}",
        job_id=job.job_id,
        task_type=job.task_type,
        idempotency_key=job.idempotency_key,
        attempt=job.attempt,
        max_attempts=job.max_attempts,
        trace_id=job.trace_id,
        requested_by=str(job.requested_by) if job.requested_by is not None else None,
        payload=dict(job.payload or {}),
    )


async def mark_job_succeeded(
    db: AsyncSession,
    *,
    job_id: int,
    result: dict[str, Any],
) -> None:
    now = datetime.now(UTC)
    job = await _load_job_for_update(db, job_id=job_id)
    if job is None:
        return
    job.status = "succeeded"
    job.result = result
    job.error_message = None
    job.finished_at = now
    job.updated_at = now


async def mark_job_failed_or_retrying(
    db: AsyncSession,
    *,
    job_id: int,
    error_message: str,
    retryable: bool,
    retry_backoff_seconds: Sequence[int],
) -> str:
    now = datetime.now(UTC)
    job = await _load_job_for_update(db, job_id=job_id)
    if job is None:
        return "missing"

    next_attempt = int(job.attempt or 0) + 1
    safe_max_attempts = max(1, int(job.max_attempts or 1))

    job.attempt = next_attempt
    job.error_message = error_message[:2000]
    job.updated_at = now

    if retryable and next_attempt < safe_max_attempts:
        delay_seconds = get_retry_delay_seconds(retry_backoff_seconds, attempt=next_attempt)
        job.status = "retrying"
        job.scheduled_at = now + timedelta(seconds=delay_seconds)
        job.finished_at = None
        return "retrying"

    job.status = "failed"
    job.finished_at = now
    return "failed"


def get_retry_delay_seconds(retry_backoff_seconds: Sequence[int], *, attempt: int) -> int:
    if not retry_backoff_seconds:
        return 60
    index = max(0, min(attempt - 1, len(retry_backoff_seconds) - 1))
    return max(1, int(retry_backoff_seconds[index]))


async def _load_job_for_update(db: AsyncSession, *, job_id: int) -> BackgroundJob | None:
    await apply_local_lock_timeout(db)
    query = select(BackgroundJob).where(BackgroundJob.job_id == job_id).with_for_update()
    return await db.scalar(query)
