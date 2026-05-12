from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from .common import CamelModel, PageQuery, PaginationMeta


class StorageUsagePoint(CamelModel):
    date: date
    used: int = Field(ge=0)


class StorageUsageTrend(CamelModel):
    trends: list[StorageUsagePoint]


class GetUsageTrendQuery(CamelModel):
    days: int = Field(default=7, ge=1, le=365)


class StorageUserItem(CamelModel):
    user_id: str
    username: str
    email: str
    storage_used: int = Field(ge=0)
    storage_limit: int = Field(gt=0)
    usage_percentage: float = Field(ge=0)
    status: str


class StorageUsersList(CamelModel):
    items: list[StorageUserItem]
    pagination: PaginationMeta


class GetStorageUsersQuery(PageQuery):
    pass


class UpdateStorageQuotaRequest(CamelModel):
    storage_limit: int = Field(gt=0)


class UpdateStorageQuotaResponse(CamelModel):
    user_id: str
    storage_limit: int = Field(gt=0)
    storage_used: int = Field(ge=0)
    usage_percentage: float = Field(ge=0)
    updated_at: datetime
