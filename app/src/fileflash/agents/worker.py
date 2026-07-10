from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..core.errors import ApiError
from ..core.settings import get_settings
from ..db.session import SessionLocal
from ..db.transaction import apply_local_lock_timeout
from ..models import BackgroundJob
from ..services.job_queue import RedisStreamJobQueue
from ..workers.contracts import WorkerJobMessage
from .harness.event_bus import AgentEventBus, AgentEventEnvelope, build_agent_event_bus
from .runtime import AgentJobCanceled, ExecuteRunner, PlanRunner

logger = logging.getLogger(__name__)


class AgentWorkerConsumer:
    def __init__(
        self,
        *,
        queue: RedisStreamJobQueue,
        session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
        event_bus: AgentEventBus | None = None,
    ) -> None:
        self._settings = get_settings()
        self._queue = queue
        self._session_factory = session_factory
        self._event_bus = event_bus or build_agent_event_bus(settings=self._settings)

    async def run(self) -> None:
        if not self._settings.redis_url:
            raise RuntimeError("REDIS_URL is required for agent worker event streaming")
        logger.info(
            "Agent worker started queue=%s group=%s concurrency=%s",
            self._settings.agent_queue_stream,
            self._settings.agent_queue_group,
            self._settings.agent_worker_concurrency,
        )
        async with asyncio.TaskGroup() as group:
            for slot in range(max(1, self._settings.agent_worker_concurrency)):
                group.create_task(self._run_slot(slot))

    async def _run_slot(self, slot: int) -> None:
        while True:
            queued = await self._queue.consume_one(block_ms=self._settings.agent_queue_block_ms)
            if queued is None:
                continue
            queue_message_id, message = queued
            try:
                await self._process_message(slot=slot, message=message)
            finally:
                await self._queue.ack(queue_message_id)

    async def _process_message(self, *, slot: int, message: WorkerJobMessage) -> None:
        job = await self._mark_running(message)
        if job is None:
            return

        started = datetime.now(UTC)
        try:
            result, phase = await asyncio.wait_for(
                self._run_job(job=job),
                timeout=self._settings.agent_job_timeout_sec,
            )
        except AgentJobCanceled:
            await self._mark_canceled(job_id=message.job_id)
            logger.info(
                "Agent slot=%s canceled jobId=%s taskType=%s",
                slot,
                message.job_id,
                message.task_type,
            )
            return
        except Exception as exc:
            await self._mark_failed(job_id=message.job_id, error=exc)
            logger.warning(
                "Agent slot=%s failed jobId=%s taskType=%s error=%s",
                slot,
                message.job_id,
                message.task_type,
                exc,
            )
            return

        await self._mark_succeeded(job_id=message.job_id, result=result, phase=phase)
        duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
        logger.info(
            "Agent slot=%s succeeded jobId=%s taskType=%s durationMs=%s traceId=%s",
            slot,
            message.job_id,
            message.task_type,
            duration_ms,
            message.trace_id,
        )

    async def _run_job(self, *, job: BackgroundJob) -> tuple[dict[str, Any], str]:
        async with self._session_factory() as db:
            fresh_job = await db.get(BackgroundJob, int(job.job_id))
            if fresh_job is None:
                raise ApiError(status_code=404, code=404, message="Job not found")
            if fresh_job.task_type == "agent.plan":
                result = await PlanRunner(
                    settings=self._settings,
                    event_bus=self._event_bus,
                ).run(db=db, job=fresh_job)
                phase = "awaiting_confirm" if result.requires_confirmation else "completed"
                return result.model_dump(by_alias=True, mode="json"), phase
            if fresh_job.task_type == "agent.execute":
                result = await ExecuteRunner(event_bus=self._event_bus).run(db=db, job=fresh_job)
                return result.model_dump(by_alias=True, mode="json"), "completed"
            raise ApiError(
                status_code=400,
                code=400,
                message=f"Unsupported agent task: {fresh_job.task_type}",
            )

    async def _mark_running(self, message: WorkerJobMessage) -> BackgroundJob | None:
        async with self._session_factory() as db:
            async with db.begin():
                await apply_local_lock_timeout(db)
                job = await db.scalar(
                    select(BackgroundJob)
                    .where(BackgroundJob.job_id == message.job_id)
                    .with_for_update()
                )
                if job is None or job.status in {"succeeded", "failed", "canceled"}:
                    return None
                now = datetime.now(UTC)
                job.status = "running"
                job.started_at = job.started_at or now
                job.updated_at = now
                job.error_message = None
                job.agent_phase = "planning" if job.task_type == "agent.plan" else "executing"
                return job

    async def _mark_succeeded(self, *, job_id: int, result: dict[str, Any], phase: str) -> None:
        safe_result = jsonable_encoder(result)
        should_publish = False
        async with self._session_factory() as db:
            async with db.begin():
                await apply_local_lock_timeout(db)
                job = await db.scalar(
                    select(BackgroundJob).where(BackgroundJob.job_id == job_id).with_for_update()
                )
                if job is None:
                    return
                if job.status == "canceled" or job.cancel_requested_at is not None:
                    return
                now = datetime.now(UTC)
                job.status = "succeeded"
                job.result = safe_result
                job.error_message = None
                job.agent_phase = phase
                job.finished_at = now
                job.updated_at = now
                should_publish = True
        if should_publish:
            await self._publish_terminal(
                job_id=job_id,
                event_type="job.succeeded",
                payload={"status": "succeeded", "agentPhase": phase, "data": {"result": safe_result}},
            )

    async def _mark_failed(self, *, job_id: int, error: Exception) -> None:
        message = _error_message(error)
        should_publish = False
        async with self._session_factory() as db:
            async with db.begin():
                await apply_local_lock_timeout(db)
                job = await db.scalar(
                    select(BackgroundJob).where(BackgroundJob.job_id == job_id).with_for_update()
                )
                if job is None:
                    return
                if job.status == "canceled" or job.cancel_requested_at is not None:
                    return
                now = datetime.now(UTC)
                job.status = "failed"
                job.agent_phase = "failed"
                job.error_message = message[:2000]
                job.finished_at = now
                job.updated_at = now
                should_publish = True
        if should_publish:
            await self._publish_terminal(
                job_id=job_id,
                event_type="job.failed",
                payload={
                    "status": "failed",
                    "agentPhase": "failed",
                    "message": message[:2000],
                    "data": {"errorMessage": message[:2000]},
                },
            )

    async def _mark_canceled(self, *, job_id: int) -> None:
        should_publish = False
        async with self._session_factory() as db:
            async with db.begin():
                await apply_local_lock_timeout(db)
                job = await db.scalar(
                    select(BackgroundJob).where(BackgroundJob.job_id == job_id).with_for_update()
                )
                if job is None:
                    return
                now = datetime.now(UTC)
                job.status = "canceled"
                job.agent_phase = "canceled"
                job.cancel_requested_at = job.cancel_requested_at or now
                job.finished_at = now
                job.updated_at = now
                should_publish = True
        if should_publish:
            await self._publish_terminal(
                job_id=job_id,
                event_type="job.canceled",
                payload={"status": "canceled", "agentPhase": "canceled"},
            )

    async def _publish_terminal(
        self,
        *,
        job_id: int,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            await self._event_bus.publish(
                AgentEventEnvelope(
                    job_id=job_id,
                    event_type=event_type,
                    payload=payload or {},
                    emitted_at=datetime.now(UTC),
                )
            )
        except Exception:
            logger.exception(
                "Failed to publish terminal event jobId=%s eventType=%s",
                job_id,
                event_type,
            )


def _error_message(error: Exception) -> str:
    if isinstance(error, ApiError):
        return f"ApiError[{error.status_code}/{error.code}]: {error.message}"
    return f"{type(error).__name__}: {error}"


async def run_agent_worker() -> None:
    settings = get_settings()
    queue = RedisStreamJobQueue(
        redis_url=settings.redis_url,
        stream_key=settings.agent_queue_stream,
        group_name=settings.agent_queue_group,
        consumer_name=f"agent-{uuid.uuid4().hex[:8]}",
    )
    consumer = AgentWorkerConsumer(queue=queue)
    try:
        await consumer.run()
    finally:
        await queue.aclose()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    try:
        asyncio.run(run_agent_worker())
    except KeyboardInterrupt:
        logger.info("Agent worker stopped by keyboard interrupt")


if __name__ == "__main__":
    main()
