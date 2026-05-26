from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from redis.exceptions import RedisError

from fileflash.core.settings import Settings
from fileflash.models.enums import UserRole, UserStatus
from fileflash.models.tables_identity import User
from fileflash.services.download_rate_limit import DownloadRateLimitService
from fileflash.services.rate_limiter import RedisRateLimiter


class FakeRedis:
    def __init__(
        self,
        *,
        fail: bool = False,
        runtime_error: RuntimeError | None = None,
        close_runtime_error: RuntimeError | None = None,
    ) -> None:
        self.fail = fail
        self.runtime_error = runtime_error
        self.close_runtime_error = close_runtime_error
        self.values: dict[str, int] = {}
        self.expired: list[tuple[str, int]] = []

    async def incrby(self, key: str, amount: int) -> int:
        if self.runtime_error is not None:
            raise self.runtime_error
        if self.fail:
            raise RedisError("down")
        self.values[key] = self.values.get(key, 0) + amount
        return self.values[key]

    async def expire(self, key: str, window_seconds: int) -> None:
        self.expired.append((key, window_seconds))

    async def aclose(self) -> None:
        if self.close_runtime_error is not None:
            raise self.close_runtime_error


@pytest.mark.asyncio
async def test_allow_weighted_uses_incrby_and_sets_ttl() -> None:
    limiter = RedisRateLimiter("redis://example")
    fake = FakeRedis()
    limiter._redis = fake  # type: ignore[assignment]

    allowed = await limiter.allow_weighted("k", limit=10, window_seconds=60, weight=4)

    assert allowed is True
    assert fake.values["k"] == 4
    assert fake.expired == [("k", 60)]


@pytest.mark.asyncio
async def test_allow_weighted_rejects_over_limit() -> None:
    limiter = RedisRateLimiter("redis://example")
    fake = FakeRedis()
    limiter._redis = fake  # type: ignore[assignment]

    assert await limiter.allow_weighted("k", limit=5, window_seconds=60, weight=4) is True
    assert await limiter.allow_weighted("k", limit=5, window_seconds=60, weight=2) is False


@pytest.mark.asyncio
async def test_allow_weighted_degrades_open_when_redis_fails() -> None:
    limiter = RedisRateLimiter("redis://example")
    limiter._redis = FakeRedis(fail=True)  # type: ignore[assignment]

    assert await limiter.allow_weighted("k", limit=1, window_seconds=60, weight=10) is True


@pytest.mark.asyncio
async def test_allow_weighted_degrades_open_and_resets_client_on_loop_runtime_error() -> None:
    limiter = RedisRateLimiter("redis://example")
    limiter._redis = FakeRedis(
        runtime_error=RuntimeError("Future pending attached to a different loop")
    )  # type: ignore[assignment]

    assert await limiter.allow_weighted("k", limit=1, window_seconds=60, weight=10) is True
    assert limiter._redis is None


@pytest.mark.asyncio
async def test_allow_weighted_reraises_non_loop_runtime_error() -> None:
    limiter = RedisRateLimiter("redis://example")
    limiter._redis = FakeRedis(runtime_error=RuntimeError("unexpected runtime failure"))  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="unexpected runtime failure"):
        await limiter.allow_weighted("k", limit=1, window_seconds=60, weight=10)


@pytest.mark.asyncio
async def test_close_ignores_loop_runtime_error() -> None:
    limiter = RedisRateLimiter("redis://example")
    limiter._redis = FakeRedis(close_runtime_error=RuntimeError("Event loop is closed"))  # type: ignore[assignment]

    await limiter.close()

    assert limiter._redis is None


class FakeRateLimiter:
    def __init__(self) -> None:
        self.allow = AsyncMock(return_value=False)
        self.allow_weighted = AsyncMock(return_value=False)


@pytest.mark.asyncio
async def test_download_rate_limiter_skips_admin_user_id() -> None:
    admin = User(
        user_id=1,
        username="admin",
        email="admin@example.com",
        password_hash="x",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        email_verified=True,
        storage_limit=1024,
        storage_used=0,
    )
    db = type("Db", (), {"get": AsyncMock(return_value=admin)})()
    rate_limiter = FakeRateLimiter()
    service = DownloadRateLimitService(
        db=db,  # type: ignore[arg-type]
        settings=Settings(DATABASE_URL="sqlite+aiosqlite:///:memory:"),
        rate_limiter=rate_limiter,  # type: ignore[arg-type]
    )

    await service.enforce_user_id(user_id=1, bytes_count=100)

    rate_limiter.allow.assert_not_awaited()
    rate_limiter.allow_weighted.assert_not_awaited()
