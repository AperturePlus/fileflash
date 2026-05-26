from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Protocol

from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis

from ...core.settings import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgentEventEnvelope:
    job_id: int
    event_type: str
    payload: dict[str, Any]
    emitted_at: datetime
    event_id: str | None = None

    def to_json(self) -> str:
        body = jsonable_encoder(asdict(self))
        return json.dumps(body, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str) -> AgentEventEnvelope:
        data = json.loads(raw)
        return cls(
            job_id=int(data["job_id"]),
            event_type=str(data["event_type"]),
            payload=dict(data.get("payload") or {}),
            emitted_at=datetime.fromisoformat(data["emitted_at"]),
            event_id=data.get("event_id"),
        )


class AgentEventStream(Protocol):
    async def next(self, *, timeout: float | None = None) -> AgentEventEnvelope: ...
    async def aclose(self) -> None: ...


class AgentEventBus(Protocol):
    async def publish(self, envelope: AgentEventEnvelope) -> None: ...

    def subscribe(
        self,
        *,
        job_id: int,
    ) -> AbstractAsyncContextManager[AgentEventStream]: ...


@dataclass(slots=True)
class _InMemoryStream:
    queue: asyncio.Queue[AgentEventEnvelope]

    async def next(self, *, timeout: float | None = None) -> AgentEventEnvelope:
        if timeout is None:
            return await self.queue.get()
        return await asyncio.wait_for(self.queue.get(), timeout=timeout)

    async def aclose(self) -> None:
        return None


class InMemoryAgentEventBus:
    def __init__(self, *, buffer_size: int = 64) -> None:
        self._buffer = buffer_size
        self._subscribers: dict[int, list[asyncio.Queue[AgentEventEnvelope]]] = {}

    async def publish(self, envelope: AgentEventEnvelope) -> None:
        queues = list(self._subscribers.get(envelope.job_id, []))
        for queue in queues:
            if queue.full():
                logger.warning(
                    "InMemoryAgentEventBus dropped event: queue full job_id=%s",
                    envelope.job_id,
                )
                continue
            await queue.put(envelope)

    @contextlib.asynccontextmanager
    async def subscribe(self, *, job_id: int) -> AsyncIterator[_InMemoryStream]:
        queue: asyncio.Queue[AgentEventEnvelope] = asyncio.Queue(maxsize=self._buffer)
        self._subscribers.setdefault(job_id, []).append(queue)
        try:
            yield _InMemoryStream(queue=queue)
        finally:
            subscribers = self._subscribers.get(job_id)
            if subscribers is not None:
                subscribers.remove(queue)
                if not subscribers:
                    del self._subscribers[job_id]


class RedisAgentEventBus:
    def __init__(
        self,
        *,
        redis: Redis,
        channel_prefix: str,
        buffer_size: int = 64,
    ) -> None:
        self._redis = redis
        self._channel_prefix = channel_prefix
        self._buffer = buffer_size

    def _channel(self, job_id: int) -> str:
        return f"{self._channel_prefix}:{job_id}:events"

    async def publish(self, envelope: AgentEventEnvelope) -> None:
        await self._redis.publish(self._channel(envelope.job_id), envelope.to_json())

    @contextlib.asynccontextmanager
    async def subscribe(self, *, job_id: int) -> AsyncIterator[_RedisStream]:
        pubsub = self._redis.pubsub()
        channel = self._channel(job_id)
        await pubsub.subscribe(channel)
        stream = _RedisStream(pubsub=pubsub)
        try:
            yield stream
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


@dataclass(slots=True)
class _RedisStream:
    pubsub: Any

    async def next(self, *, timeout: float | None = None) -> AgentEventEnvelope:
        if timeout is None:
            async for message in self.pubsub.listen():
                envelope = _envelope_from_redis_message(message)
                if envelope is not None:
                    return envelope
        else:
            message = await self.pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=timeout,
            )
            envelope = _envelope_from_redis_message(message)
            if envelope is not None:
                return envelope
        raise TimeoutError("No event within timeout")

    async def aclose(self) -> None:
        await self.pubsub.aclose()


def _envelope_from_redis_message(message: Any) -> AgentEventEnvelope | None:
    if message is None:
        return None
    message_type = message.get("type")
    if message_type not in {"message", "pmessage"}:
        return None
    data = message.get("data")
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return AgentEventEnvelope.from_json(str(data))


def build_agent_event_bus(
    *,
    settings: Settings | None = None,
    redis: Redis | None = None,
) -> AgentEventBus:
    cfg = settings or get_settings()
    if redis is None:
        if not cfg.redis_url:
            return InMemoryAgentEventBus(buffer_size=cfg.agent_event_bus_buffer_size)
        redis = Redis.from_url(cfg.redis_url, decode_responses=True)
    return RedisAgentEventBus(
        redis=redis,
        channel_prefix=cfg.agent_event_channel_prefix,
        buffer_size=cfg.agent_event_bus_buffer_size,
    )


__all__ = [
    "AgentEventBus",
    "AgentEventEnvelope",
    "AgentEventStream",
    "InMemoryAgentEventBus",
    "RedisAgentEventBus",
    "build_agent_event_bus",
]
