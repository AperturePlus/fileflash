from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from .common import CamelModel, PageQuery

UserRole = Literal["user", "admin"]
UserStatus = Literal["active", "suspended"]
AppLanguage = Literal["zh-CN", "en-US"]


class UserPreference(CamelModel):
    language: AppLanguage


class User(CamelModel):
    user_id: str
    username: str
    email: str
    storage_limit: int = Field(ge=0)
    storage_used: int = Field(ge=0)
    created_at: datetime
    role: UserRole | None = None
    status: UserStatus | None = None
    email_verified: bool = False
    email_verified_at: datetime | None = None
    preference: UserPreference | None = None


class UserGroupInfo(CamelModel):
    group_id: str
    group_name: str
    role: Literal["admin", "member"]


class UserProfile(User):
    groups: list[UserGroupInfo]
    updated_at: datetime
    last_login: datetime | None


class UpdateProfileRequest(CamelModel):
    username: str | None = Field(default=None, min_length=2, max_length=100)
    email: str | None = None


class UpdateUserPreferenceRequest(CamelModel):
    language: AppLanguage | None = None


class ChangePasswordRequest(CamelModel):
    old_password: str | None = Field(default=None, min_length=6, max_length=255)
    new_password: str | None = Field(default=None, min_length=6, max_length=255)


class BreakdownDetail(CamelModel):
    size: int = Field(ge=0)
    count: int = Field(ge=0)


class StorageStats(CamelModel):
    storage_limit: int = Field(ge=0)
    storage_used: int = Field(ge=0)
    storage_available: int = Field(ge=0)
    storage_percentage: float = Field(ge=0)
    file_count: int = Field(ge=0)
    folder_count: int = Field(ge=0)
    breakdown: dict[str, BreakdownDetail]


class ActivityItem(CamelModel):
    id: int
    operation: str
    details: dict[str, str | int]
    ip_address: str
    performed_at: datetime


class GetActivityLogQuery(PageQuery):
    operation: str | None = None


class GetUsersQuery(PageQuery):
    search: str | None = None


class UpdateUserStatusRequest(CamelModel):
    status: UserStatus


class UpdateUserStatusResponse(CamelModel):
    user_id: str
    status: UserStatus
    updated_at: datetime


class ViolationItem(CamelModel):
    id: str
    file_id: str
    file_name: str
    type: str
    level: str
    reported_at: datetime
    status: str


class ResolveViolationResponse(CamelModel):
    violation_id: str
    resolved_at: datetime
