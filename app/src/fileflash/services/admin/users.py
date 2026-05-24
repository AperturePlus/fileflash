from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...models.enums import UserRole, UserStatus
from ...models.tables_identity import User, UserSession
from ...schemas.admin.users import AdminUserItem, ListAdminUsersQuery, UpdateUserStatusResponse
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

        last_seen_map = await self._collect_last_seen([int(row.user_id) for row in rows])
        items = [self._to_item(row, last_seen_map.get(int(row.user_id))) for row in rows]
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
    def _to_item(row: User, last_active_at: datetime | None) -> AdminUserItem:
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
        )


__all__ = ["AdminUsersService"]
