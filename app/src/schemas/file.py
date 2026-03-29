from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from .common import CamelModel, PageQuery

FileSortField = Literal["name", "size", "createdAt", "updatedAt"]
SortOrder = Literal["asc", "desc"]


class FileItem(CamelModel):
    item_type: Literal["file"] = "file"
    id: str
    name: str
    size: int = Field(ge=0)
    mime_type: str
    owner_name: str
    updated_at: datetime
    created_at: datetime
    folder_id: str
    permission: Literal["read", "write", "owner"] | None = None
    is_starred: bool | None = None


class FolderItem(CamelModel):
    item_type: Literal["folder"] = "folder"
    id: str
    name: str
    size: int = Field(ge=0)
    owner_name: str
    updated_at: datetime
    created_at: datetime
    parent_folder_id: str | None = None
    permission: Literal["read", "write", "owner"] | None = None
    is_starred: bool | None = None


ContentItem = Annotated[FileItem | FolderItem, Field(discriminator="item_type")]


class GetFilesQuery(PageQuery):
    folder_id: str | None = None
    sort: FileSortField | None = None
    order: SortOrder | None = None
    search: str | None = None
    mime_type: str | None = None


class GetFolderContentsQuery(PageQuery):
    folder_id: str
    sort: FileSortField | None = None
    order: SortOrder | None = None
    search: str | None = None


class PathItem(CamelModel):
    folder_id: str | None = None
    name: str


class FolderPathResponse(CamelModel):
    full_path: str
    path_items: list[PathItem]


class CreateFolderRequest(CamelModel):
    folder_name: str = Field(min_length=1, max_length=255)
    parent_folder_id: str | None = None


class RenameFolderRequest(CamelModel):
    folder_name: str = Field(min_length=1, max_length=255)


class MoveFolderRequest(CamelModel):
    target_parent_id: str


class MoveFolderResponse(CamelModel):
    folder_id: str
    target_parent_id: str
    moved_at: datetime


class DeleteFolderResponse(CamelModel):
    folder_id: str
    folder_name: str
    deleted_at: datetime


class FolderSizeResponse(CamelModel):
    total_size: int = Field(ge=0)
    file_count: int = Field(ge=0)
    folder_count: int = Field(ge=0)


class CopyFolderRequest(CamelModel):
    target_parent_id: str
    new_name: str | None = Field(default=None, min_length=1, max_length=255)


class ToggleFolderStarRequest(CamelModel):
    is_starred: bool


class UploadPreflightRequest(CamelModel):
    file_hash: str = Field(min_length=8, max_length=128)
    file_name: str = Field(min_length=1, max_length=255)
    file_size: int = Field(gt=0)
    mime_type: str = Field(min_length=1, max_length=255)
    parent_id: str


class UploadPreflightResponse(CamelModel):
    status: Literal["COMPLETE", "UPLOADING"]
    file_id: str | None = None
    upload_id: str | None = None
    chunk_size: int | None = Field(default=None, gt=0)
    uploaded_chunk_indexes: list[int] | None = None


class MergeChunksRequest(CamelModel):
    file_hash: str = Field(min_length=8, max_length=128)
    file_name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=255)
    parent_id: str


class MergeChunksResponse(CamelModel):
    file_id: str
    file_name: str
    file_size: int = Field(ge=0)
    mime_type: str
    folder_id: str
    object_hash: str
    created_at: datetime
    download_url: str


class FileDetails(FileItem):
    status: bool


class RenameFileRequest(CamelModel):
    file_name: str = Field(min_length=1, max_length=255)


class MoveFileRequest(CamelModel):
    target_folder_id: str


class MoveFileResponse(CamelModel):
    file_id: str
    target_folder_id: str
    moved_at: datetime


class CopyFileRequest(CamelModel):
    target_folder_id: str
    new_name: str | None = Field(default=None, min_length=1, max_length=255)


class CopyFileResponse(CamelModel):
    file_id: str
    original_file_id: str
    target_folder_id: str
    new_name: str | None = None
    copied_at: datetime


class ToggleFileStarRequest(CamelModel):
    is_starred: bool


class DeleteFileResponse(CamelModel):
    file_id: str
    file_name: str
    deleted_at: datetime


class BatchFilesRequest(CamelModel):
    action: Literal["delete", "move", "copy"]
    file_ids: list[str] = Field(min_length=1)
    target_folder_id: str | None = None


class BatchFilesResponse(CamelModel):
    processed: int = Field(ge=0)
    action: Literal["delete", "move", "copy"]
    succeeded: int = Field(ge=0)


class GetAdminFilesQuery(PageQuery):
    search: str | None = None
    virus_status: Literal["clean", "pending", "flagged"] | None = None
    sort: FileSortField | None = None
    order: SortOrder | None = None


class AdminFileAuditItem(CamelModel):
    id: str
    name: str
    size: int = Field(ge=0)
    mime_type: str
    hash: str
    virus_status: Literal["clean", "pending", "flagged"]
    is_shared: bool
    owner_name: str
    updated_at: datetime
    created_at: datetime


class RescanAdminFileResponse(CamelModel):
    file_id: str
    virus_status: Literal["clean", "pending", "flagged"]
    scanned_at: datetime
