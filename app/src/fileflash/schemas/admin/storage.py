from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from ..common import CamelModel, PageQuery


class AdminStorageSummary(CamelModel):
    storage_used: int
    storage_limit: int
    storage_percentage: float
    file_count: int
    user_count: int
    updated_at: datetime


class AdminStorageUserItem(CamelModel):
    user_id: str
    username: str
    email: str
    storage_limit: int
    storage_used: int
    usage_percentage: float
    updated_at: datetime


class ListStorageUsersQuery(PageQuery):
    sort: Literal["storageUsed", "usagePercentage", "username"] = "storageUsed"
    order: Literal["asc", "desc"] = "desc"


class UpdateQuotaRequest(CamelModel):
    storage_limit: int = Field(ge=0)


class UpdateQuotaResponse(CamelModel):
    user_id: str
    storage_limit: int
    storage_used: int
    usage_percentage: float
    updated_at: datetime


class UsageTrendQuery(CamelModel):
    days: Literal[7, 14, 30] = 7


class UsageTrendPoint(CamelModel):
    date: str
    used: int


class UsageTrendResponse(CamelModel):
    trends: list[UsageTrendPoint]
    is_estimated: bool = False


__all__ = [
    "AdminStorageSummary",
    "AdminStorageUserItem",
    "ListStorageUsersQuery",
    "UpdateQuotaRequest",
    "UpdateQuotaResponse",
    "UsageTrendQuery",
    "UsageTrendPoint",
    "UsageTrendResponse",
]
