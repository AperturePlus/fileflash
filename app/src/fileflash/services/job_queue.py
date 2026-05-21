from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from ..workers.contracts import WorkerJobMessage


class JobQueuePublisher(Protocol):
    async def publish(self, message: WorkerJobMessage) -> str: ...


class RedisStreamJobQueue:
    def __init__(
        self,
        *,
        redis_url: str | None,
        stream_key: str,
        group_name: str | None = None,
        consumer_name: str | None = None,
    ) -> None:
        self._redis_url = redis_url
        self._stream_key = stream_key
        self._group_name = group_name
        self._consumer_name = consumer_name or f"worker-{uuid.uuid4().hex[:8]}"
        self._redis: Redis | None = None
        self._group_ready = False

    async def publish(self, message: WorkerJobMessage) -> str:
        redis = await self._client()
        payload = json.dumps(asdict(message), separators=(",", ":"), ensure_ascii=False)
        return await redis.xadd(self._stream_key, {"message": payload})

    async def consume_one(self, *, block_ms: int) -> tuple[str, WorkerJobMessage] | None:
        redis = await self._client()
        group_name = self._group_name
        if not group_name:
            raise RuntimeError("consume_one requires group_name")
        await self._ensure_group(redis)

        records = await redis.xreadgroup(
            groupname=group_name,
            consumername=self._consumer_name,
            streams={self._stream_key: ">"},
            count=1,
            block=block_ms,
        )
        if not records:
            return None

        _, items = records[0]
        if not items:
            return None

        message_id, field_map = items[0]
        raw_message = field_map.get("message")
        if not raw_message:
            raise RuntimeError("Queue message missing 'message' field")
        payload = json.loads(raw_message)
        return message_id, WorkerJobMessage(**payload)

    async def ack(self, message_id: str) -> None:
        redis = await self._client()
        group_name = self._group_name
        if not group_name:
            raise RuntimeError("ack requires group_name")
        await redis.xack(self._stream_key, group_name, message_id)

    async def aclose(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
            self._group_ready = False

    async def _client(self) -> Redis:
        if not self._redis_url:
            raise RuntimeError("Redis URL is required for job queue")
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def _ensure_group(self, redis: Redis) -> None:
        if self._group_ready or not self._group_name:
            return
        try:
            await redis.xgroup_create(
                name=self._stream_key,
                groupname=self._group_name,
                id="$",
                mkstream=True,
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        self._group_ready = True
