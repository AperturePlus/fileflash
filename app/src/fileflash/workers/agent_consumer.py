from __future__ import annotations

import asyncio
import logging

from ..agents.processor import process_agent_job
from ..core import get_settings
from ..db.session import SessionLocal
from ..services.job_queue import RedisStreamJobQueue

logger = logging.getLogger(__name__)


class AgentWorkerConsumer:
    def __init__(
        self,
        *,
        queue: RedisStreamJobQueue,
        concurrency: int,
        block_ms: int,
    ) -> None:
        self._queue = queue
        self._concurrency = max(1, concurrency)
        self._block_ms = block_ms

    async def run(self) -> None:
        settings = get_settings()
        logger.info(
            "Agent worker started: slots=%s stream=%s group=%s",
            self._concurrency,
            settings.agent_queue_stream,
            settings.agent_queue_group,
        )
        async with asyncio.TaskGroup() as task_group:
            for slot in range(self._concurrency):
                task_group.create_task(self._run_slot(slot))

    async def _run_slot(self, slot: int) -> None:
        while True:
            queued = await self._queue.consume_one(block_ms=self._block_ms)
            if queued is None:
                continue
            message_id, message = queued
            try:
                await process_agent_job(message.job_id, session_factory=SessionLocal)
            except Exception:
                logger.exception("Agent worker slot %s failed job %s", slot, message.job_id)
            finally:
                await self._queue.ack(message_id)


async def _main() -> None:
    settings = get_settings()
    if not settings.redis_url:
        raise SystemExit("REDIS_URL is required for agent worker")
    queue = RedisStreamJobQueue(
        redis_url=settings.redis_url,
        stream_key=settings.agent_queue_stream,
        group_name=settings.agent_queue_group,
    )
    consumer = AgentWorkerConsumer(
        queue=queue,
        concurrency=settings.agent_worker_concurrency,
        block_ms=settings.agent_queue_block_ms,
    )
    try:
        await consumer.run()
    finally:
        await queue.aclose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())


if __name__ == "__main__":
    main()
