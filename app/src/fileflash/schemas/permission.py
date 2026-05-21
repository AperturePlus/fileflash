from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import model_validator

from .common import CamelModel, PageQuery


class CreatePermissionRequest(CamelModel):
    file_id: str | None = None
    folder_id: str | None = None
    user_id: str | None = None
    group_id: str | None = None
    permission: Literal["read", "write", "admin"]

    @model_validator(mode="after")
    def validate_target(self) -> "CreatePermissionRequest":
        has_file = self.file_id is not None
        has_folder = self.folder_id is not None
        has_user = self.user_id is not None
        has_group = self.group_id is not None

        if has_file == has_folder:
            raise ValueError("Exactly one of fileId or folderId is required")
        if has_user == has_group:
            raise ValueError("Exactly one of userId or groupId is required")
        return self


class GrantedTo(CamelModel):
    type: Literal["user", "group"]
    id: str
    name: str


class PermissionItem(CamelModel):
    permission_id: str
    item_type: Literal["file", "folder"]
    item_id: str
    granted_to: GrantedTo
    permission: Literal["read", "write", "admin"]
    created_at: datetime


class UpdatePermissionRequest(CamelModel):
    permission: Literal["read", "write", "admin"]


class GetPermissionsQuery(PageQuery):
    file_id: str | None = None
    folder_id: str | None = None


class DeletePermissionResponse(CamelModel):
    permission_id: str
    revoked_permission: Literal["read", "write", "admin"]
    deleted_at: datetime
