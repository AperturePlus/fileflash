from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from .common import CamelModel, PageQuery


class ShareSettings(CamelModel):
    password_protected: bool
    password: str | None = None
    expire_at: datetime | None = None
    allow_download: bool
    allow_preview: bool


class SharedItemInfo(CamelModel):
    id: str
    name: str
    size: int = Field(ge=0)
    mime_type: str
    folder_path: str | None = None


class Share(CamelModel):
    share_id: str
    share_link: str
    item_type: Literal["file", "folder"]
    item_info: SharedItemInfo
    settings: ShareSettings
    created_at: datetime
    visit_count: int | None = Field(default=None, ge=0)
    download_count: int | None = Field(default=None, ge=0)


class CreateShareRequest(CamelModel):
    resource_type: Literal["file", "folder"]
    resource_id: str


class AccessShareRequest(CamelModel):
    password: str | None = None


class AccessUrls(CamelModel):
    download: str
    preview: str


class AccessShareResponseData(CamelModel):
    access_token: str
    expires_in: int = Field(ge=1)
    item_type: Literal["file", "folder"]
    item_info: SharedItemInfo
    access_urls: AccessUrls


class GetSharesQuery(PageQuery):
    pass


class UpdateShareSettingsRequest(CamelModel):
    password_protected: bool | None = None
    password: str | None = Field(default=None, min_length=4, max_length=64)
    regenerate_password: bool | None = None
    expire_at: datetime | None = None
    allow_download: bool | None = None
    allow_preview: bool | None = None


class GetSharedItemsQuery(PageQuery):
    sort: Literal["name", "size", "sharedAt", "sharedBy"] | None = None
    order: Literal["asc", "desc"] | None = None


class SharedItem(CamelModel):
    item_type: Literal["file", "folder"]
    id: str
    name: str
    size: int = Field(ge=0)
    mime_type: str | None = None
    shared_by: str
    permission: Literal["read", "write"]
    shared_at: datetime


class DeleteShareResponse(CamelModel):
    share_id: str
    share_link: str
    deleted_at: datetime


class AcceptSharedItemResponse(CamelModel):
    accepted: bool
    accepted_at: datetime
    item_id: str


class SaveShareRequest(CamelModel):
    target_folder_id: str = Field(min_length=1, max_length=255)
    share_access_token: str = Field(min_length=8, max_length=4096)


class SaveShareResponse(CamelModel):
    saved_at: datetime
    item_type: Literal["file", "folder"]
    item_id: str
    target_folder_id: str
