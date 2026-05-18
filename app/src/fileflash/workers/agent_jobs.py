from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.transaction import apply_local_lock_timeout
from ..models import BackgroundJob


async def set_agent_phase(
    db: AsyncSession,
    *,
    job_id: int,
    agent_phase: str,
) -> None:
    job = await _load_job_for_update(db, job_id=job_id)
    if job is None:
        return
    job.agent_phase = agent_phase
    job.updated_at = datetime.now(UTC)


async def mark_agent_job_succeeded(
    db: AsyncSession,
    *,
    job_id: int,
    result: dict[str, Any],
    agent_phase: str,
) -> None:
    now = datetime.now(UTC)
    job = await _load_job_for_update(db, job_id=job_id)
    if job is None:
        return
    job.status = "succeeded"
    job.result = result
    job.agent_phase = agent_phase
    job.error_message = None
    job.finished_at = now
    job.updated_at = now


async def mark_agent_job_failed(
    db: AsyncSession,
    *,
    job_id: int,
    error_message: str,
    agent_phase: str = "failed",
) -> None:
    now = datetime.now(UTC)
    job = await _load_job_for_update(db, job_id=job_id)
    if job is None:
        return
    job.status = "failed"
    job.agent_phase = agent_phase
    job.error_message = error_message[:2000]
    job.finished_at = now
    job.updated_at = now


async def mark_agent_job_canceled(
    db: AsyncSession,
    *,
    job_id: int,
) -> None:
    now = datetime.now(UTC)
    job = await _load_job_for_update(db, job_id=job_id)
    if job is None:
        return
    job.status = "canceled"
    job.agent_phase = "canceled"
    job.cancel_requested_at = job.cancel_requested_at or now
    job.finished_at = now
    job.updated_at = now


async def request_agent_job_cancel(
    db: AsyncSession,
    *,
    job_id: int,
) -> BackgroundJob | None:
    now = datetime.now(UTC)
    job = await _load_job_for_update(db, job_id=job_id)
    if job is None:
        return None
    job.cancel_requested_at = now
    job.updated_at = now
    if job.status in {"pending", "running", "retrying"}:
        job.status = "canceled"
        job.agent_phase = "canceled"
        job.finished_at = now
    return job


async def _load_job_for_update(db: AsyncSession, *, job_id: int) -> BackgroundJob | None:
    await apply_local_lock_timeout(db)
    query = select(BackgroundJob).where(BackgroundJob.job_id == job_id).with_for_update()
    return await db.scalar(query)
