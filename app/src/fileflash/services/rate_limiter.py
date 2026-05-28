from __future__ import annotations

import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)
_LOOP_RUNTIME_ERROR_MARKERS = ("different loop", "attached to a different loop", "event loop is closed")


class RedisRateLimiter:
    def __init__(self, redis_url: str | None) -> None:
        self._redis_url = redis_url
        self._redis: Redis | None = None

    async def _client(self) -> Redis | None:
        if not self._redis_url:
            return None
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        return await self.allow_weighted(key=key, limit=limit, window_seconds=window_seconds, weight=1)

    async def allow_weighted(self, key: str, limit: int, window_seconds: int, weight: int) -> bool:
        client = await self._client()
        if client is None:
            return True

        normalized_weight = max(0, int(weight))
        try:
            current = await client.incrby(key, normalized_weight)
            if current == normalized_weight:
                await client.expire(key, window_seconds)
            return current <= limit
        except RedisError:
            logger.exception("Redis unavailable, rate limiter degraded for key=%s", key)
            return True
        except RuntimeError as exc:
            if not _is_loop_runtime_error(exc):
                raise
            logger.exception("Redis loop error, rate limiter degraded for key=%s", key)
            await self._drop_cached_client()
            return True

    async def close(self) -> None:
        client = self._redis
        self._redis = None
        if client is None:
            return
        try:
            await client.aclose()
        except RuntimeError as exc:
            if _is_loop_runtime_error(exc):
                logger.warning("Ignore Redis close loop error: %s", exc)
                return
            raise

    async def _drop_cached_client(self) -> None:
        client = self._redis
        self._redis = None
        if client is None:
            return
        try:
            await client.aclose()
        except RuntimeError as exc:
            if _is_loop_runtime_error(exc):
                logger.warning("Ignore Redis reset loop error: %s", exc)
                return
            raise


def _is_loop_runtime_error(exc: RuntimeError) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _LOOP_RUNTIME_ERROR_MARKERS)

