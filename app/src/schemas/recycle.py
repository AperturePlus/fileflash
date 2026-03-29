from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from .common import CamelModel, PageQuery


class RecycleBinItem(CamelModel):
    item_type: Literal["file", "folder"]
    id: str
    name: str
    original_path: str
    size: int = Field(ge=0)
    mime_type: str | None = None
    folder_id: str | None = None
    folder_name: str | None = None
    deleted_at: datetime
    auto_delete_at: datetime
    days_until_permanent_delete: int = Field(ge=0)
    can_restore: bool
    restore_conflicts: bool


class GetRecycleBinQuery(PageQuery):
    item_type: Literal["file", "folder"] | None = None


class RestoreRecycleItemRequest(CamelModel):
    item_type: Literal["file", "folder"]
    target_folder_id: str | None = None


class RestoreRecycleItemResponse(CamelModel):
    item_type: Literal["file", "folder"]
    id: str
    name: str
    restored_to: str | None = None
    restored_at: datetime


class PermanentDeleteResponse(CamelModel):
    item_type: Literal["file", "folder"]
    id: str
    name: str
    permanently_deleted_at: datetime


class ClearRecycleBinResponse(CamelModel):
    files_deleted: int = Field(ge=0)
    folders_deleted: int = Field(ge=0)
    total_storage_freed: int = Field(ge=0)
    cleanup_completed_at: datetime
