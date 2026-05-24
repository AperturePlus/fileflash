from __future__ import annotations

from datetime import datetime
from typing import Literal

from ..common import CamelModel, PageQuery

ExternalUserStatus = Literal["active", "suspended", "pending_verification"]


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


class ListAdminUsersQuery(PageQuery):
    search: str | None = None
    status: Literal["active", "suspended"] | None = None
    role: Literal["USER", "ADMIN"] | None = None
    sort: Literal["username", "createdAt", "storageUsed"] = "createdAt"
    order: Literal["asc", "desc"] = "desc"


class UpdateUserStatusRequest(CamelModel):
    status: Literal["active", "suspended"]


class UpdateUserStatusResponse(CamelModel):
    user_id: str
    status: ExternalUserStatus
    updated_at: datetime


__all__ = [
    "AdminUserItem",
    "ListAdminUsersQuery",
    "UpdateUserStatusRequest",
    "UpdateUserStatusResponse",
]
