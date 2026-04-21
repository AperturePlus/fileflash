from __future__ import annotations

from datetime import datetime
from typing import Any

from ..models import BackgroundJob
from .common import CamelModel


class BackgroundJobResponse(CamelModel):
    job_id: str
    task_type: str
    status: str
    priority: int
    payload: dict[str, Any]
    result: dict[str, Any]
    error_message: str | None = None
    attempt: int
    max_attempts: int
    scheduled_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    trace_id: str | None = None
    idempotency_key: str | None = None
    requested_by: str | None = None
    created_at: datetime
    updated_at: datetime


def to_background_job_response(job: BackgroundJob) -> BackgroundJobResponse:
    return BackgroundJobResponse(
        job_id=str(job.job_id),
        task_type=str(job.task_type),
        status=str(job.status),
        priority=int(job.priority or 0),
        payload=dict(job.payload or {}),
        result=dict(job.result or {}),
        error_message=job.error_message,
        attempt=int(job.attempt or 0),
        max_attempts=int(job.max_attempts or 0),
        scheduled_at=job.scheduled_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        trace_id=job.trace_id,
        idempotency_key=job.idempotency_key,
        requested_by=str(job.requested_by) if job.requested_by is not None else None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )

