from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...models.enums import UploadTaskStatus, UserRole, UserStatus
from ...models.tables_identity import User, UserSession
from ...models.tables_storage import UploadTask
from ...models.tables_worker import BackgroundJob
from ...schemas.admin.users import (
    AdminUserItem,
    AdminUserUsageStats,
    ListAdminUsersQuery,
    UpdateUserStatusResponse,
)
from ...schemas.common import PaginatedData, PaginationMeta
from ._status import external_to_internal, internal_to_external


class AdminUsersService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_users(self, *, query: ListAdminUsersQuery) -> PaginatedData[AdminUserItem]:
        statement = select(User).where(User.deleted_at.is_(None))
        if query.search:
            keyword = f"%{query.search.strip().lower()}%"
            statement = statement.where(
                func.lower(User.username).like(keyword) | func.lower(User.email).like(keyword)
            )
        if query.status:
            statement = statement.where(User.status == external_to_internal(query.status))
        if query.role:
            statement = statement.where(User.role == UserRole(query.role))

        sort_column = {
            "username": User.username,
            "createdAt": User.created_at,
            "storageUsed": User.storage_used,
        }[query.sort]
        statement = statement.order_by(sort_column.desc() if query.order == "desc" else sort_column.asc())

        total = await self.db.scalar(select(func.count()).select_from(statement.subquery()))
        total_items = int(total or 0)
        total_pages = max(1, -(-total_items // query.per_page))
        offset = (query.page - 1) * query.per_page
        rows = list(await self.db.scalars(statement.offset(offset).limit(query.per_page)))

        user_ids = [int(row.user_id) for row in rows]
        last_seen_map = await self._collect_last_seen(user_ids)
        usage_from, usage_to = self._resolve_usage_window(query)
        usage_map = await self._collect_usage_stats(
            user_ids=user_ids,
            usage_from=usage_from,
            usage_to=usage_to,
        )
        items = [
            self._to_item(
                row,
                last_seen_map.get(int(row.user_id)),
                usage_map.get(
                    int(row.user_id),
                    AdminUserUsageStats(traffic_bytes=0, agent_tokens=0),
                ),
            )
            for row in rows
        ]
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

    @staticmethod
    def _resolve_usage_window(query: ListAdminUsersQuery) -> tuple[datetime, datetime]:
        try:
            return query.resolve_usage_window()
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message=str(exc)) from exc

    async def _collect_usage_stats(
        self,
        *,
        user_ids: list[int],
        usage_from: datetime,
        usage_to: datetime,
    ) -> dict[int, AdminUserUsageStats]:
        if not user_ids:
            return {}

        traffic_rows = await self.db.execute(
            select(UploadTask.user_id, func.coalesce(func.sum(UploadTask.total_size), 0))
            .where(
                and_(
                    UploadTask.user_id.in_(user_ids),
                    UploadTask.status == UploadTaskStatus.COMPLETED,
                    UploadTask.completed_at.is_not(None),
                    UploadTask.completed_at >= usage_from,
                    UploadTask.completed_at <= usage_to,
                )
            )
            .group_by(UploadTask.user_id)
        )
        stats: dict[int, AdminUserUsageStats] = {
            int(user_id): AdminUserUsageStats(traffic_bytes=int(total or 0), agent_tokens=0)
            for user_id, total in traffic_rows.all()
        }

        token_expr = BackgroundJob.result["costEstimate"]["tokens"].as_integer()
        agent_rows = await self.db.execute(
            select(
                BackgroundJob.requested_by,
                func.coalesce(func.sum(func.coalesce(token_expr, 0)), 0),
            )
            .where(
                and_(
                    BackgroundJob.requested_by.in_(user_ids),
                    BackgroundJob.task_type == "agent.plan",
                    BackgroundJob.status == "succeeded",
                    BackgroundJob.finished_at.is_not(None),
                    BackgroundJob.finished_at >= usage_from,
                    BackgroundJob.finished_at <= usage_to,
                )
            )
            .group_by(BackgroundJob.requested_by)
        )
        for user_id, total in agent_rows.all():
            if user_id is None:
                continue
            key = int(user_id)
            current = stats.get(key, AdminUserUsageStats(traffic_bytes=0, agent_tokens=0))
            stats[key] = AdminUserUsageStats(
                traffic_bytes=current.traffic_bytes,
                agent_tokens=int(total or 0),
            )

        return stats

    async def set_status(self, *, user_id: int, external_status: str) -> UpdateUserStatusResponse:
        target = await self.db.get(User, user_id)
        if target is None or target.deleted_at is not None:
            raise ApiError(status_code=404, code=404, message="User not found")

        new_internal = external_to_internal(external_status)
        if (
            new_internal == UserStatus.DISABLED
            and target.role == UserRole.ADMIN
            and target.status == UserStatus.ACTIVE
        ):
            remaining = await self.db.scalar(
                select(func.count(User.user_id)).where(
                    and_(
                        User.role == UserRole.ADMIN,
                        User.status == UserStatus.ACTIVE,
                        User.user_id != user_id,
                        User.deleted_at.is_(None),
                    )
                )
            )
            if int(remaining or 0) == 0:
                raise ApiError(
                    status_code=409,
                    code=409,
                    message="Cannot suspend the last active admin",
                )

        target.status = new_internal
        target.updated_at = datetime.now(UTC)
        if new_internal == UserStatus.DISABLED:
            now = datetime.now(UTC)
            await self.db.execute(
                update(UserSession)
                .where(and_(UserSession.user_id == user_id, UserSession.revoked_at.is_(None)))
                .values(revoked_at=now, last_seen_at=now)
            )

        await self.db.commit()
        await self.db.refresh(target)
        return UpdateUserStatusResponse(
            user_id=str(target.user_id),
            status=internal_to_external(target.status),
            updated_at=target.updated_at,
        )

    async def _collect_last_seen(self, user_ids: list[int]) -> dict[int, datetime]:
        if not user_ids:
            return {}
        rows = await self.db.execute(
            select(UserSession.user_id, func.max(UserSession.last_seen_at))
            .where(and_(UserSession.user_id.in_(user_ids), UserSession.revoked_at.is_(None)))
            .group_by(UserSession.user_id)
        )
        return {int(user_id): seen for user_id, seen in rows.all()}

    @staticmethod
    def _to_item(
        row: User,
        last_active_at: datetime | None,
        usage_stats: AdminUserUsageStats,
    ) -> AdminUserItem:
        limit = max(int(row.storage_limit), 1)
        return AdminUserItem(
            user_id=str(row.user_id),
            username=row.username,
            email=row.email,
            role=row.role.value if hasattr(row.role, "value") else str(row.role),
            status=internal_to_external(row.status),
            email_verified=bool(row.email_verified),
            email_verified_at=row.email_verified_at,
            storage_limit=int(row.storage_limit),
            storage_used=int(row.storage_used),
            usage_percentage=round((int(row.storage_used) / limit) * 100, 2),
            last_login_at=row.last_login_at,
            last_active_at=last_active_at,
            created_at=row.created_at,
            usage_stats=usage_stats,
        )


__all__ = ["AdminUsersService"]
