from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...agents.processor import schedule_agent_job
from ...core.settings import Settings, get_settings
from ...models import BackgroundJob
from ..background_jobs import BackgroundJobService, _build_queue_message

logger = logging.getLogger(__name__)


class AgentBackgroundJobService(BackgroundJobService):
    """Enqueue agent jobs and optionally process inline when Redis is unavailable."""

    async def enqueue_agent(
        self,
        db: AsyncSession,
        *,
        task_type: str,
        payload: dict[str, Any],
        requested_by: int,
        agent_phase: str,
        idempotency_key: str | None = None,
        settings: Settings | None = None,
    ) -> BackgroundJob:
        settings = settings or get_settings()
        logger.info(
            "agent.enqueue start task_type=%s user_id=%s phase=%s redis=%s inline=%s",
            task_type,
            requested_by,
            agent_phase,
            bool(settings.redis_url),
            settings.agent_inline_processing,
        )
        now = datetime.now(UTC)
        job = BackgroundJob(
            task_type=task_type,
            status="pending",
            payload=payload,
            result={},
            error_message=None,
            attempt=0,
            max_attempts=3,
            scheduled_at=now,
            trace_id=None,
            idempotency_key=idempotency_key,
            requested_by=requested_by,
            priority=100,
            agent_phase=agent_phase,
        )
        db.add(job)
        await db.flush()
        await db.commit()

        published = await self._try_publish(job, settings=settings)
        logger.info(
            "agent.enqueue persisted job_id=%s published=%s inline=%s",
            job.job_id,
            published,
            settings.agent_inline_processing,
        )
        # Dev default: process in API process even when Redis publish succeeds (no worker required).
        if settings.agent_inline_processing:
            logger.info("agent.enqueue scheduling inline processor job_id=%s", job.job_id)
            schedule_agent_job(job.job_id)
        elif not published:
            job.status = "failed"
            job.error_message = "Agent job queue unavailable"
            job.finished_at = datetime.now(UTC)
            job.updated_at = datetime.now(UTC)
            await db.commit()
            from ...core.errors import ApiError

            raise ApiError(
                status_code=503,
                code=503,
                message="Agent job queue unavailable",
                data={"jobId": str(job.job_id)},
            )
        return job

    async def _try_publish(self, job: BackgroundJob, *, settings: Settings) -> bool:
        if self._queue_publisher is None:
            return False
        if not settings.redis_url:
            return False
        try:
            await self._queue_publisher.publish(_build_queue_message(job))
            return True
        except Exception as exc:
            logger.warning("Agent queue publish failed for job %s: %s", job.job_id, exc)
            return settings.agent_inline_processing
