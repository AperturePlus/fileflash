from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .enums import (
    FileStatus,
    FolderStatus,
    FolderType,
    PreviewStatus,
    ScanResult,
    UploadMode,
    UploadPartStatus,
    UploadStatus,
    UploadTaskStatus,
)
from .pg import pg_enum
from .types import UTCDateTime as DateTime


class StorageObject(Base):
    __tablename__ = "storage_object"
    __table_args__ = (
        UniqueConstraint("bucket_name", "object_key", name="uk_bucket_object_key"),
        Index(
            "uk_storage_object_hash_algo_size",
            "hash_algorithm",
            "object_hash",
            "object_size",
            unique=True,
            postgresql_where=text("object_hash IS NOT NULL"),
        ),
        Index("idx_storage_object_scan_status", "scan_status"),
        Index("idx_storage_object_moderation_status", "moderation_status"),
        Index("idx_storage_object_upload_status", "upload_status"),
    )

    object_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    object_hash: Mapped[str | None] = mapped_column(CHAR(64))
    hash_algorithm: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'sha256'"),
    )
    bucket_name: Mapped[str] = mapped_column(String(100), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    object_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    etag: Mapped[str | None] = mapped_column(String(128))
    version_id: Mapped[str | None] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(255))
    storage_class: Mapped[str | None] = mapped_column(String(50))
    upload_status: Mapped[UploadStatus] = mapped_column(
        pg_enum(UploadStatus, "upload_status_enum"),
        nullable=False,
        server_default=text("'active'"),
    )
    scan_status: Mapped[ScanResult] = mapped_column(
        pg_enum(ScanResult, "scan_result_enum"),
        nullable=False,
        server_default=text("'pending'"),
    )
    moderation_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'pending'"),
    )
    quarantined_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime)
    object_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    ref_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)


class Folder(Base):
    __tablename__ = "folder"
    __table_args__ = (
        Index(
            "uk_folder_root_name_active",
            "owner_id",
            "folder_name",
            unique=True,
            postgresql_where=text("parent_folder_id IS NULL AND status = 'active'"),
        ),
        Index(
            "uk_folder_child_name_active",
            "owner_id",
            "parent_folder_id",
            "folder_name",
            unique=True,
            postgresql_where=text("parent_folder_id IS NOT NULL AND status = 'active'"),
        ),
        Index("idx_folder_owner_parent_status", "owner_id", "parent_folder_id", "status"),
        Index(
            "idx_folder_name_trgm",
            text("(LOWER(folder_name)) gin_trgm_ops"),
            postgresql_using="gin",
        ),
    )

    folder_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_folder_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("folder.folder_id", ondelete="CASCADE"),
    )
    folder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cached_size: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    status: Mapped[FolderStatus] = mapped_column(
        pg_enum(FolderStatus, "folder_status_enum"),
        nullable=False,
        server_default=text("'active'"),
    )
    folder_type: Mapped[FolderType] = mapped_column(
        pg_enum(FolderType, "folder_type_enum"),
        nullable=False,
        server_default=text("'normal'"),
    )
    deleted_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="SET NULL"),
    )
    restored_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)


class File(Base):
    __tablename__ = "file"
    __table_args__ = (
        Index(
            "uk_file_name_active_in_folder",
            "owner_id",
            "folder_id",
            "file_name",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("idx_file_last_accessed_at", "last_accessed_at"),
        Index(
            "idx_file_name_trgm",
            text("(LOWER(file_name)) gin_trgm_ops"),
            postgresql_using="gin",
        ),
        Index("idx_file_storage_object_id", "storage_object_id"),
        Index("idx_file_owner_folder", "owner_id", "folder_id", "status"),
    )

    file_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    uploader_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    folder_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("folder.folder_id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_ext: Mapped[str | None] = mapped_column(String(50))
    mime_type: Mapped[str | None] = mapped_column(String(255))
    storage_object_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("storage_object.object_id"),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    status: Mapped[FileStatus] = mapped_column(
        pg_enum(FileStatus, "file_status_enum"),
        nullable=False,
        server_default=text("'active'"),
    )
    deleted_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="SET NULL"),
    )
    restored_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)


class UploadTask(Base):
    __tablename__ = "upload_task"
    __table_args__ = (
        UniqueConstraint("bucket_name", "object_key", "upload_id", name="uk_upload_target"),
        Index("idx_upload_task_user_status", "user_id", "status"),
        Index("idx_upload_task_expired_at", "expired_at"),
        Index(
            "uk_upload_task_user_client_file_id",
            "user_id",
            "client_file_id",
            unique=True,
            postgresql_where=text("client_file_id IS NOT NULL"),
        ),
    )

    task_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    folder_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("folder.folder_id", ondelete="SET NULL"),
    )
    file_name: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(255))
    bucket_name: Mapped[str] = mapped_column(String(100), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    object_hash: Mapped[str | None] = mapped_column(CHAR(64))
    total_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chunk_size: Mapped[int | None] = mapped_column(BigInteger)
    uploaded_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    client_file_id: Mapped[str | None] = mapped_column(String(255))
    upload_id: Mapped[str | None] = mapped_column(String(255))
    upload_mode: Mapped[UploadMode] = mapped_column(
        pg_enum(UploadMode, "upload_mode_enum"),
        nullable=False,
        server_default=text("'single'"),
    )
    status: Mapped[UploadTaskStatus] = mapped_column(
        pg_enum(UploadTaskStatus, "upload_task_status_enum"),
        nullable=False,
        server_default=text("'init'"),
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class UploadTaskPart(Base):
    __tablename__ = "upload_task_part"
    __table_args__ = (
        UniqueConstraint("task_id", "part_number", name="uk_task_part"),
        Index("idx_upload_task_part_task_status", "task_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("upload_task.task_id", ondelete="CASCADE"),
        nullable=False,
    )
    part_number: Mapped[int] = mapped_column(Integer, nullable=False)
    etag: Mapped[str | None] = mapped_column(String(128))
    part_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[UploadPartStatus] = mapped_column(
        pg_enum(UploadPartStatus, "upload_part_status_enum"),
        nullable=False,
        server_default=text("'pending'"),
    )
    checksum: Mapped[str | None] = mapped_column(CHAR(64))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class FilePreviewAsset(Base):
    __tablename__ = "file_preview_asset"
    __table_args__ = (
        Index(
            "uk_file_preview_asset_type_page",
            "source_object_id",
            "preview_type",
            text("(COALESCE(page_no, -1))"),
            unique=True,
        ),
    )

    preview_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    source_object_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("storage_object.object_id", ondelete="CASCADE"),
        nullable=False,
    )
    preview_object_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("storage_object.object_id", ondelete="SET NULL"),
    )
    preview_type: Mapped[str] = mapped_column(String(50), nullable=False)
    page_no: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(255))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[PreviewStatus] = mapped_column(
        pg_enum(PreviewStatus, "preview_status_enum"),
        nullable=False,
        server_default=text("'pending'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class FileMediaMetadata(Base):
    __tablename__ = "file_media_metadata"

    metadata_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    source_object_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("storage_object.object_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    page_count: Mapped[int | None] = mapped_column(Integer)
    bitrate: Mapped[int | None] = mapped_column(Integer)
    sample_rate: Mapped[int | None] = mapped_column(Integer)
    video_codec: Mapped[str | None] = mapped_column(String(64))
    audio_codec: Mapped[str | None] = mapped_column(String(64))
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class BatchDownloadTask(Base):
    __tablename__ = "batch_download_task"
    __table_args__ = (
        Index("idx_batch_download_task_user_status", "user_id", "status"),
    )

    task_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    archive_name: Mapped[str] = mapped_column(String(255), nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    items: Mapped[list[dict[str, Any]] | list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'pending'"))
    storage_object_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("storage_object.object_id", ondelete="SET NULL"),
    )
    expire_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


__all__ = [
    "BatchDownloadTask",
    "File",
    "FileMediaMetadata",
    "FilePreviewAsset",
    "Folder",
    "StorageObject",
    "UploadTask",
    "UploadTaskPart",
]
