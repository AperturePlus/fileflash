from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..core.settings import Settings
from ..models.enums import UserRole
from ..models.tables_identity import User
from .rate_limiter import RedisRateLimiter


class DownloadRateLimitService:
    def __init__(
        self,
        *,
        db: AsyncSession,
        settings: Settings,
        rate_limiter: RedisRateLimiter,
    ) -> None:
        self.db = db
        self.settings = settings
        self.rate_limiter = rate_limiter

    async def enforce_user(self, *, user: User, bytes_count: int) -> None:
        if user.role == UserRole.ADMIN:
            return
        await self._enforce(scope=f"user:{int(user.user_id)}", bytes_count=bytes_count)

    async def enforce_user_id(self, *, user_id: int, bytes_count: int) -> None:
        user = await self.db.get(User, user_id)
        if user is not None and user.role == UserRole.ADMIN:
            return
        await self._enforce(scope=f"user:{int(user_id)}", bytes_count=bytes_count)

    async def enforce_share_ip(self, *, client_ip: str, bytes_count: int) -> None:
        await self._enforce(scope=f"share-ip:{client_ip}", bytes_count=bytes_count)

    async def _enforce(self, *, scope: str, bytes_count: int) -> None:
        window_seconds = max(1, int(self.settings.download_rate_window_seconds))
        request_limit = max(1, int(self.settings.download_rate_limit_requests))
        byte_limit = max(1, int(self.settings.download_rate_limit_bytes))
        normalized_bytes = max(0, int(bytes_count))

        request_allowed = await self.rate_limiter.allow(
            key=f"download-rate:{scope}:requests",
            limit=request_limit,
            window_seconds=window_seconds,
        )
        if not request_allowed:
            raise ApiError(status_code=429, code=429, message="Download rate limit exceeded")

        bytes_allowed = await self.rate_limiter.allow_weighted(
            key=f"download-rate:{scope}:bytes",
            limit=byte_limit,
            window_seconds=window_seconds,
            weight=normalized_bytes,
        )
        if not bytes_allowed:
            raise ApiError(status_code=429, code=429, message="Download bandwidth limit exceeded")


__all__ = ["DownloadRateLimitService"]
