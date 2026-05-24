from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import Float, and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...models.tables_audit_security import Log
from ...models.tables_identity import User
from ...models.tables_storage import File
from ...schemas.admin.storage import (
    AdminStorageSummary,
    AdminStorageUserItem,
    ListStorageUsersQuery,
    UpdateQuotaResponse,
    UsageTrendPoint,
    UsageTrendQuery,
    UsageTrendResponse,
)
from ...schemas.common import PaginatedData, PaginationMeta

_STORAGE_EVENT_OPS = ("file.created", "file.deleted", "file.restored")
_TREND_CACHE_TTL = 300


class AdminStorageService:
    def __init__(self, db: AsyncSession, redis: Redis | None) -> None:
        self.db = db
        self.redis = redis

    async def summary(self) -> AdminStorageSummary:
        used_sum = await self.db.scalar(
            select(func.coalesce(func.sum(User.storage_used), 0)).where(User.deleted_at.is_(None))
        )
        limit_sum = await self.db.scalar(
            select(func.coalesce(func.sum(User.storage_limit), 0)).where(User.deleted_at.is_(None))
        )
        file_count = await self.db.scalar(
            select(func.count(File.file_id)).where(File.deleted_at.is_(None))
        )
        user_count = await self.db.scalar(
            select(func.count(User.user_id)).where(User.deleted_at.is_(None))
        )

        used = int(used_sum or 0)
        limit = int(limit_sum or 0)
        return AdminStorageSummary(
            storage_used=used,
            storage_limit=limit,
            storage_percentage=round((used / limit) * 100, 2) if limit else 0.0,
            file_count=int(file_count or 0),
            user_count=int(user_count or 0),
            updated_at=datetime.now(UTC),
        )

    async def list_storage_users(self, *, query: ListStorageUsersQuery) -> PaginatedData[AdminStorageUserItem]:
        usage_ratio = case(
            (User.storage_limit > 0, User.storage_used.cast(Float) / User.storage_limit.cast(Float)),
            else_=0.0,
        )
        sort_column = {
            "storageUsed": User.storage_used,
            "usagePercentage": usage_ratio,
            "username": User.username,
        }[query.sort]

        statement = (
            select(User)
            .where(User.deleted_at.is_(None))
            .order_by(sort_column.desc() if query.order == "desc" else sort_column.asc())
        )

        total = await self.db.scalar(select(func.count()).select_from(statement.subquery()))
        total_items = int(total or 0)
        total_pages = max(1, -(-total_items // query.per_page))
        offset = (query.page - 1) * query.per_page
        rows = list(await self.db.scalars(statement.offset(offset).limit(query.per_page)))
        items = [self._to_item(row) for row in rows]
        return PaginatedData(
            items=items,
            pagination=PaginationMeta(
                total_items=total_items,
                total_pages=total_pages,
                per_page=query.per_page,
                current_page=query.page,
                has_prev=query.page > 1,
                has_next=query.page < total_pages,
            ),
        )

    async def update_quota(self, *, user_id: int, new_limit: int) -> UpdateQuotaResponse:
        target = await self.db.get(User, user_id, with_for_update=True)
        if target is None or target.deleted_at is not None:
            raise ApiError(status_code=404, code=404, message="User not found")
        if new_limit < int(target.storage_used):
            raise ApiError(status_code=409, code=409, message="New quota cannot be below current usage")

        target.storage_limit = int(new_limit)
        target.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(target)
        return UpdateQuotaResponse(
            user_id=str(target.user_id),
            storage_limit=int(target.storage_limit),
            storage_used=int(target.storage_used),
            usage_percentage=round((int(target.storage_used) / max(int(target.storage_limit), 1)) * 100, 2),
            updated_at=target.updated_at,
        )

    async def usage_trend(self, *, query: UsageTrendQuery) -> UsageTrendResponse:
        cached = await self._cache_get(query.days)
        if cached is not None:
            return cached

        current_total = int(
            await self.db.scalar(
                select(func.coalesce(func.sum(User.storage_used), 0)).where(User.deleted_at.is_(None))
            )
            or 0
        )
        cutoff = datetime.now(UTC) - timedelta(days=query.days)
        rows = await self.db.execute(
            select(Log.operation, Log.metadata_payload, Log.performed_at)
            .where(Log.operation.in_(_STORAGE_EVENT_OPS))
            .where(Log.performed_at >= cutoff)
        )
        events = rows.all()

        deltas: dict[date, int] = {}
        for operation, metadata_payload, performed_at in events:
            if performed_at is None:
                continue
            size = int((metadata_payload or {}).get("size") or 0)
            sign = 1 if operation in {"file.created", "file.restored"} else -1
            day = performed_at.astimezone(UTC).date()
            deltas[day] = deltas.get(day, 0) + sign * size

        today = datetime.now(UTC).date()
        points: list[UsageTrendPoint] = []
        running = current_total
        for offset in range(query.days):
            day = today - timedelta(days=offset)
            points.append(UsageTrendPoint(date=day.isoformat(), used=max(running, 0)))
            running -= deltas.get(day, 0)
        points.reverse()

        result = UsageTrendResponse(trends=points, is_estimated=not events)
        await self._cache_set(query.days, result)
        return result

    @staticmethod
    def _to_item(row: User) -> AdminStorageUserItem:
        limit = max(int(row.storage_limit), 1)
        return AdminStorageUserItem(
            user_id=str(row.user_id),
            username=row.username,
            email=row.email,
            storage_limit=int(row.storage_limit),
            storage_used=int(row.storage_used),
            usage_percentage=round((int(row.storage_used) / limit) * 100, 2),
            updated_at=row.updated_at,
        )

    async def _cache_get(self, days: int) -> UsageTrendResponse | None:
        if self.redis is None:
            return None
        try:
            raw = await self.redis.get(f"admin:storage:trend:{days}")
        except Exception:
            return None
        if not raw:
            return None
        return UsageTrendResponse.model_validate_json(raw)

    async def _cache_set(self, days: int, payload: UsageTrendResponse) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.setex(
                f"admin:storage:trend:{days}",
                _TREND_CACHE_TTL,
                payload.model_dump_json(by_alias=True),
            )
        except Exception:
            return


__all__ = ["AdminStorageService"]
