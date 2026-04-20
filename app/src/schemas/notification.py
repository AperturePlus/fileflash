from __future__ import annotations

from datetime import datetime

from .common import CamelModel, PageQuery, PaginationMeta


class NotificationItem(CamelModel):
    id: int
    message: str
    is_read: bool
    created_at: datetime


class NotificationsList(CamelModel):
    items: list[NotificationItem]
    pagination: PaginationMeta
    unread_count: int
    total_count: int


class GetNotificationsQuery(PageQuery):
    is_read: bool | None = None


class MarkAsReadResponse(CamelModel):
    notification_id: int
    updated_at: datetime


class MarkAllAsReadResponse(CamelModel):
    updated_count: int


class DeleteNotificationResponse(CamelModel):
    notification_id: int


class BroadcastNotificationRequest(CamelModel):
    message: str
