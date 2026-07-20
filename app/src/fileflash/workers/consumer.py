from __future__ import annotations

import asyncio
import logging
import uuid
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..core import get_settings
from ..core.errors import ApiError
from ..db.session import SessionLocal
from ..s3.minio_client import MinioObjectStorageClient
from ..services.background_jobs import BackgroundJobService
from ..services.job_queue import RedisStreamJobQueue
from ..services.upload import UploadService
from .bootstrap import WorkerRuntimeConfig, build_worker_runtime_config, create_process_pool
from .contracts import WorkerJobMessage
from .dispatcher import PicklableRemoteTaskError, execute_task
from .effects import apply_task_effects, mark_transcode_failed, mark_transcode_running
from .repository import (
    get_retry_delay_seconds,
    mark_job_failed_or_retrying,
    mark_job_running,
    mark_job_succeeded,
)

logger = logging.getLogger(__name__)


class WorkerConsumer:
    def __init__(
        self,
        *,
        config: WorkerRuntimeConfig,
        executor: ProcessPoolExecutor,
        queue: RedisStreamJobQueue,
        session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
    ) -> None:
        self._config = config
        self._executor = executor
        self._queue = queue
        self._session_factory = session_factory
        self._settings = get_settings()
        self._storage = MinioObjectStorageClient.from_settings(self._settings)
        self._job_publisher = RedisStreamJobQueue(
            redis_url=self._settings.redis_url,
            stream_key=self._settings.worker_queue_stream,
        )
        self._jobs = BackgroundJobService(queue_publisher=self._job_publisher)

    async def run(self) -> None:
        logger.info(
            "Worker started: slots=%s queue=%s group=%s timeout=%ss",
            self._config.worker_slots,
            self._config.queue_stream,
            self._config.queue_group,
            self._config.task_timeout_seconds,
        )
        async with asyncio.TaskGroup() as task_group:
            for slot in range(self._config.worker_slots):
                task_group.create_task(self._run_slot(slot))

    async def _run_slot(self, slot: int) -> None:
        while True:
            queued = await self._queue.consume_one(block_ms=self._config.queue_block_ms)
            if queued is None:
                continue
            queue_message_id, queued_message = queued
            try:
                message = await self._mark_running(queued_message)
                if message is None:
                    continue
                await self._process_message(slot=slot, message=message)
            finally:
                await self._queue.ack(queue_message_id)

    async def _mark_running(self, message: WorkerJobMessage) -> WorkerJobMessage | None:
        async with self._session_factory() as db:
            async with db.begin():
                return await mark_job_running(
                    db,
                    job_id=message.job_id,
                    default_max_attempts=self._config.default_max_attempts,
                )

    async def _process_message(self, *, slot: int, message: WorkerJobMessage) -> None:
        payload = dict(message.payload)
        if payload.get("jobId") in (None, ""):
            payload["jobId"] = message.job_id
        if message.task_type == "task.upload_merge":
            await self._process_upload_merge(slot=slot, message=message, payload=payload)
            return
        if message.task_type in ("task.transcode", "media.transcode"):
            payload.setdefault("ffmpegBinary", self._config.ffmpeg_binary)
            payload.setdefault("ffprobeBinary", self._config.ffprobe_binary)
            payload.setdefault("profileVersion", "mp4-v1")
            await self._mark_transcode_running(payload)

        started_at = datetime.now(UTC)
        try:
            loop = asyncio.get_running_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    self._executor,
                    execute_task,
                    message.task_type,
                    payload,
                ),
                timeout=self._config.task_timeout_seconds,
            )
        except Exception as exc:
            await self._handle_failure(slot=slot, message=message, error=exc)
            return

        try:
            async with self._session_factory() as db:
                async with db.begin():
                    extra_result = await apply_task_effects(
                        db,
                        task_type=message.task_type,
                        payload=payload,
                        result=result,
                    )
                    merged = _merge_job_result(result, extra_result)
                    merged.pop("manifestPath", None)
                    await mark_job_succeeded(db, job_id=message.job_id, result=merged)
        except Exception as exc:
            await self._handle_failure(slot=slot, message=message, error=exc)
            return

        duration_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
        logger.info(
            "Worker slot=%s succeeded jobId=%s taskType=%s attempt=%s durationMs=%s traceId=%s",
            slot,
            message.job_id,
            message.task_type,
            message.attempt,
            duration_ms,
            message.trace_id,
        )

    async def _process_upload_merge(
        self,
        *,
        slot: int,
        message: WorkerJobMessage,
        payload: dict[str, Any],
    ) -> None:
        started_at = datetime.now(UTC)
        try:
            result = await asyncio.wait_for(
                self._run_upload_merge(payload=payload),
                timeout=self._config.task_timeout_seconds,
            )
        except Exception as exc:
            await self._handle_failure(slot=slot, message=message, error=exc)
            return

        try:
            async with self._session_factory() as db:
                async with db.begin():
                    await mark_job_succeeded(db, job_id=message.job_id, result=result)
        except Exception as exc:
            await self._handle_failure(slot=slot, message=message, error=exc)
            return

        duration_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
        logger.info(
            "Worker slot=%s succeeded jobId=%s taskType=%s attempt=%s durationMs=%s traceId=%s",
            slot,
            message.job_id,
            message.task_type,
            message.attempt,
            duration_ms,
            message.trace_id,
        )

    async def _run_upload_merge(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        async with self._session_factory() as db:
            service = UploadService(
                db=db,
                settings=self._settings,
                storage=self._storage,
                jobs=self._jobs,
            )
            return await service.execute_merge_job(payload=payload)

    async def _handle_failure(
        self,
        *,
        slot: int,
        message: WorkerJobMessage,
        error: Exception,
    ) -> None:
        retryable = _is_retryable_error(error)
        if isinstance(error, ApiError):
            error_message = f"ApiError[{error.status_code}/{error.code}]: {error.message}"
        else:
            error_message = f"{type(error).__name__}: {error}"
        async with self._session_factory() as db:
            async with db.begin():
                state = await mark_job_failed_or_retrying(
                    db,
                    job_id=message.job_id,
                    error_message=error_message,
                    retryable=retryable,
                    retry_backoff_seconds=self._config.retry_backoff_seconds,
                )
                if state == "failed" and message.task_type in ("task.transcode", "media.transcode"):
                    await mark_transcode_failed(
                        db,
                        payload=dict(message.payload),
                        error_message=error_message,
                    )

        if state == "retrying":
            next_attempt = message.attempt + 1
            delay_seconds = get_retry_delay_seconds(
                self._config.retry_backoff_seconds,
                attempt=next_attempt,
            )
            retry_message = WorkerJobMessage(
                version=message.version,
                message_id=f"job-{message.job_id}-attempt-{next_attempt}",
                job_id=message.job_id,
                task_type=message.task_type,
                idempotency_key=message.idempotency_key,
                attempt=next_attempt,
                max_attempts=message.max_attempts,
                trace_id=message.trace_id,
                requested_by=message.requested_by,
                payload=dict(message.payload),
            )
            asyncio.create_task(self._republish_after_delay(retry_message, delay_seconds))

        logger.warning(
            (
                "Worker slot=%s failed jobId=%s taskType=%s attempt=%s "
                "status=%s retryable=%s traceId=%s error=%s"
            ),
            slot,
            message.job_id,
            message.task_type,
            message.attempt,
            state,
            retryable,
            message.trace_id,
            error_message,
        )

    async def _republish_after_delay(self, message: WorkerJobMessage, delay_seconds: int) -> None:
        await asyncio.sleep(delay_seconds)
        await self._queue.publish(message)

    async def _mark_transcode_running(self, payload: dict[str, Any]) -> None:
        async with self._session_factory() as db:
            async with db.begin():
                await mark_transcode_running(db, payload=payload)

    async def aclose(self) -> None:
        await self._job_publisher.aclose()


def _is_retryable_error(error: Exception) -> bool:
    if isinstance(error, ApiError):
        if error.status_code >= 500:
            return True
        if isinstance(error.data, dict) and error.data.get("retryable") is True:
            return True
        return False

    if isinstance(error, PicklableRemoteTaskError) and error.retryable_hint is not None:
        return bool(error.retryable_hint)

    if isinstance(error, PicklableRemoteTaskError):
        non_retryable_original_types = {"FileNotFoundError", "PermissionError", "ValueError"}
        if error.original_type in non_retryable_original_types:
            return False

    non_retryable_types = (FileNotFoundError, PermissionError, ValueError)
    return not isinstance(error, non_retryable_types)


def _merge_job_result(base: dict[str, Any], extra: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(base or {})
    if not extra:
        return merged

    for key, value in extra.items():
        if key == "summary" and isinstance(value, dict) and isinstance(merged.get("summary"), dict):
            merged_summary = dict(merged["summary"])
            merged_summary.update(value)
            merged["summary"] = merged_summary
            continue
        merged[key] = value
    return merged


async def run_worker() -> None:
    settings = get_settings()
    config = build_worker_runtime_config(settings)
    queue = RedisStreamJobQueue(
        redis_url=settings.redis_url,
        stream_key=config.queue_stream,
        group_name=config.queue_group,
        consumer_name=f"worker-{uuid.uuid4().hex[:8]}",
    )
    with create_process_pool(config) as executor:
        consumer = WorkerConsumer(config=config, executor=executor, queue=queue)
        try:
            await consumer.run()
        finally:
            await consumer.aclose()
            await queue.aclose()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by keyboard interrupt")


if __name__ == "__main__":
    main()
