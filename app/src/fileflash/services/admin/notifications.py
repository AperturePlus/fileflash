from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import AsyncIterator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...models.enums import UserStatus
from ...models.tables_audit_security import Notification
from ...models.tables_identity import User
from ...schemas.admin.notifications import (
    AdminNotificationItem,
    BroadcastRequest,
    BroadcastResponse,
    ListAdminNotificationsQuery,
)
from ...schemas.common import PaginatedData, PaginationMeta

MAX_BROADCAST_RECIPIENTS = 50_000
_CHUNK_SIZE = 500


class AdminNotificationsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_notifications(
        self,
        *,
        query: ListAdminNotificationsQuery,
    ) -> PaginatedData[AdminNotificationItem]:
        statement = select(Notification)
        if query.status:
            statement = statement.where(Notification.status == query.status)
        if query.type:
            statement = statement.where(Notification.notification_type == query.type)
        statement = statement.order_by(Notification.created_at.desc(), Notification.id.desc())

        total = int(await self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        total_pages = max(1, -(-total // query.per_page))
        offset = (query.page - 1) * query.per_page
        rows = list(await self.db.scalars(statement.offset(offset).limit(query.per_page)))
        items = [self._to_item(row) for row in rows]
        return PaginatedData(
            items=items,
            pagination=PaginationMeta(
                total_items=total,
                total_pages=total_pages,
                per_page=query.per_page,
                current_page=query.page,
                has_prev=query.page > 1,
                has_next=query.page < total_pages,
            ),
        )

    async def broadcast(self, *, payload: BroadcastRequest, sender_id: int) -> BroadcastResponse:
        message = (payload.message or "").strip()
        if not message:
            raise ApiError(status_code=422, code=422, message="Broadcast message cannot be empty")

        recipient_count = int(
            await self.db.scalar(
                select(func.count(User.user_id)).where(
                    User.status == UserStatus.ACTIVE,
                    User.deleted_at.is_(None),
                )
            )
            or 0
        )
        if recipient_count > MAX_BROADCAST_RECIPIENTS:
            raise ApiError(
                status_code=422,
                code=422,
                message=f"Recipient count {recipient_count} exceeds limit {MAX_BROADCAST_RECIPIENTS}",
            )

        broadcast_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        delivered = 0
        async for chunk in self._iter_active_user_ids():
            rows = [
                Notification(
                    user_id=user_id,
                    title=payload.title,
                    notification_type=payload.type,
                    channel="in_app",
                    message=message,
                    payload={"broadcastId": broadcast_id},
                    sender_user_id=sender_id,
                    status="sent",
                    sent_at=now,
                    is_read=False,
                    created_at=now,
                    updated_at=now,
                )
                for user_id in chunk
            ]
            if rows:
                self.db.add_all(rows)
                await self.db.commit()
                delivered += len(rows)

        return BroadcastResponse(
            broadcast_id=broadcast_id,
            recipient_count=delivered,
            sent_at=now,
        )

    async def archive(self, *, notification_id: int) -> None:
        row = await self.db.get(Notification, notification_id)
        if row is None:
            raise ApiError(status_code=404, code=404, message="Notification not found")
        row.status = "archived"
        row.updated_at = datetime.now(UTC)
        await self.db.commit()

    async def _iter_active_user_ids(self) -> AsyncIterator[list[int]]:
        stream = await self.db.scalars(
            select(User.user_id).where(User.status == UserStatus.ACTIVE, User.deleted_at.is_(None))
        )
        buffer: list[int] = []
        for user_id in stream:
            buffer.append(int(user_id))
            if len(buffer) >= _CHUNK_SIZE:
                yield buffer
                buffer = []
        if buffer:
            yield buffer

    @staticmethod
    def _to_item(row: Notification) -> AdminNotificationItem:
        return AdminNotificationItem(
            id=str(row.id),
            message=row.message,
            title=row.title,
            type=row.notification_type,
            status=row.status,
            is_read=bool(row.is_read),
            created_at=row.created_at or datetime.now(UTC),
            updated_at=row.updated_at,
            recipient_count=None,
        )


__all__ = ["AdminNotificationsService", "MAX_BROADCAST_RECIPIENTS"]
