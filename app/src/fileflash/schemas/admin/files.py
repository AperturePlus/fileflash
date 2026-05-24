from __future__ import annotations

from datetime import datetime
from typing import Literal

from ..common import CamelModel, PageQuery

VirusStatus = Literal["clean", "pending", "flagged"]


class AdminFileAuditItem(CamelModel):
    id: str
    name: str
    size: int
    mime_type: str
    hash: str
    virus_status: VirusStatus
    is_shared: bool
    owner_name: str
    updated_at: datetime
    created_at: datetime


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


__all__ = ["AdminFileAuditItem", "ListAdminFilesQuery", "RescanResponse", "VirusStatus"]
