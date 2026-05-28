from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import Field

from ..common import CamelModel, PageQuery

ExternalUserStatus = Literal["active", "suspended", "pending_verification"]

DEFAULT_USAGE_WINDOW = timedelta(days=7)
MAX_USAGE_WINDOW = timedelta(days=90)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class AdminUserUsageStats(CamelModel):
    traffic_bytes: int = Field(ge=0)
    agent_tokens: int = Field(ge=0)


class AdminUserItem(CamelModel):
    user_id: str
    username: str
    email: str
    role: str
    status: ExternalUserStatus
    email_verified: bool
    email_verified_at: datetime | None = None
    storage_limit: int
    storage_used: int
    usage_percentage: float
    last_login_at: datetime | None = None
    last_active_at: datetime | None = None
    created_at: datetime
    usage_stats: AdminUserUsageStats


class ListAdminUsersQuery(PageQuery):
    search: str | None = None
    status: Literal["active", "suspended"] | None = None
    role: Literal["USER", "ADMIN"] | None = None
    sort: Literal["username", "createdAt", "storageUsed"] = "createdAt"
    order: Literal["asc", "desc"] = "desc"
    usage_from: datetime | None = None
    usage_to: datetime | None = None

    def resolve_usage_window(self, *, now: datetime | None = None) -> tuple[datetime, datetime]:
        resolved_now = _normalize_datetime(now or datetime.now(UTC))
        if self.usage_from is None and self.usage_to is None:
            return resolved_now - DEFAULT_USAGE_WINDOW, resolved_now
        if self.usage_from is None or self.usage_to is None:
            raise ValueError("usageFrom and usageTo must be provided together")

        usage_from = _normalize_datetime(self.usage_from)
        usage_to = _normalize_datetime(self.usage_to)
        if usage_from > usage_to:
            raise ValueError("usageFrom must be earlier than or equal to usageTo")
        if usage_to - usage_from > MAX_USAGE_WINDOW:
            raise ValueError("usage window must not exceed 90 days")
        return usage_from, usage_to


class UpdateUserStatusRequest(CamelModel):
    status: Literal["active", "suspended"]


class UpdateUserStatusResponse(CamelModel):
    user_id: str
    status: ExternalUserStatus
    updated_at: datetime


__all__ = [
    "AdminUserItem",
    "AdminUserUsageStats",
    "ListAdminUsersQuery",
    "UpdateUserStatusRequest",
    "UpdateUserStatusResponse",
]
