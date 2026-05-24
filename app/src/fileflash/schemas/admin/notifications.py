from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from ..common import CamelModel, PageQuery


class AdminNotificationItem(CamelModel):
    id: str
    message: str
    title: str | None
    type: str
    status: str
    is_read: bool
    created_at: datetime
    updated_at: datetime
    recipient_count: int | None = None


class ListAdminNotificationsQuery(PageQuery):
    status: str | None = None
    type: str | None = None


class BroadcastRequest(CamelModel):
    title: str | None = Field(default=None, max_length=255)
    message: str = Field(min_length=1, max_length=2000)
    type: Literal["system", "announcement"] = "system"


class BroadcastResponse(CamelModel):
    broadcast_id: str
    recipient_count: int
    sent_at: datetime


__all__ = [
    "AdminNotificationItem",
    "BroadcastRequest",
    "BroadcastResponse",
    "ListAdminNotificationsQuery",
]
