from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from ..common import CamelModel, PageQuery

VirusStatus = Literal["clean", "pending", "flagged"]


class AdminFileLatestScan(CamelModel):
    scan_type: str
    scan_result: str
    virus_status: VirusStatus
    scanned_at: datetime
    details: dict[str, Any] | None = None


class AdminFileAuditItem(CamelModel):
    id: str
    object_id: str
    name: str
    size: int
    mime_type: str
    hash: str
    virus_status: VirusStatus
    is_shared: bool
    owner_name: str
    upload_count: int
    owner_count: int
    scanned_at: datetime | None = None
    updated_at: datetime
    created_at: datetime


class AdminFileAuditOwner(CamelModel):
    user_id: str
    username: str
    email: str
    file_count: int
    first_uploaded_at: datetime
    last_uploaded_at: datetime


class AdminFileAuditDetail(AdminFileAuditItem):
    object_hash: str | None = None
    hash_algorithm: str
    storage_status: str
    latest_scan: AdminFileLatestScan | None = None
    owners: list[AdminFileAuditOwner]


class ListAdminFilesQuery(PageQuery):
    search: str | None = None
    virus_status: VirusStatus | None = None
    owner_id: str | None = None
    mime_type: str | None = None
    sort: Literal["name", "size", "createdAt", "updatedAt"] = "updatedAt"
    order: Literal["asc", "desc"] = "desc"


class RescanResponse(CamelModel):
    file_id: str
    virus_status: VirusStatus
    scanned_at: datetime


__all__ = [
    "AdminFileAuditDetail",
    "AdminFileAuditItem",
    "AdminFileAuditOwner",
    "AdminFileLatestScan",
    "ListAdminFilesQuery",
    "RescanResponse",
    "VirusStatus",
]
