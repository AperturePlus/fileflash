from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .enums import (
    FavoriteItemType,
    ShareMemberStatus,
    ShareStatus,
    SortBy,
    SortDirection,
    ViewMode,
)
from .pg import pg_enum


class Acl(Base):
    __tablename__ = "acl"
    __table_args__ = (
        CheckConstraint("num_nonnulls(user_id, group_id) = 1", name="chk_acl_subject_exactly_one"),
        CheckConstraint("num_nonnulls(file_id, folder_id) = 1", name="chk_acl_resource_exactly_one"),
        Index(
            "uk_acl_file_user",
            "file_id",
            "user_id",
            unique=True,
            postgresql_where=text("file_id IS NOT NULL AND user_id IS NOT NULL"),
        ),
        Index(
            "uk_acl_file_group",
            "file_id",
            "group_id",
            unique=True,
            postgresql_where=text("file_id IS NOT NULL AND group_id IS NOT NULL"),
        ),
        Index(
            "uk_acl_folder_user",
            "folder_id",
            "user_id",
            unique=True,
            postgresql_where=text("folder_id IS NOT NULL AND user_id IS NOT NULL"),
        ),
        Index(
            "uk_acl_folder_group",
            "folder_id",
            "group_id",
            unique=True,
            postgresql_where=text("folder_id IS NOT NULL AND group_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    file_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("file.file_id", ondelete="CASCADE"),
    )
    folder_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("folder.folder_id", ondelete="CASCADE"),
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
    )
    group_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user_group.id", ondelete="CASCADE"),
    )
    permission: Mapped[str] = mapped_column(String(100), nullable=False)
    permission_role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'viewer'"),
    )
    can_preview: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    can_download: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    can_save: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    can_share: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    expire_at: Mapped[datetime | None] = mapped_column(DateTime)
    granted_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="SET NULL"),
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


class Share(Base):
    __tablename__ = "share"
    __table_args__ = (
        CheckConstraint("num_nonnulls(file_id, folder_id) = 1", name="chk_share_target"),
        CheckConstraint(
            "(max_visits IS NULL OR max_visits >= 0) AND (max_downloads IS NULL OR max_downloads >= 0)",
            name="chk_share_limits",
        ),
        Index("uk_share_code", "share_code", unique=True),
        Index("idx_share_user_status", "user_id", "status"),
        Index("idx_share_expire_time", "expire_time"),
    )

    share_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("file.file_id", ondelete="CASCADE"),
    )
    folder_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("folder.folder_id", ondelete="CASCADE"),
    )
    share_link: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    share_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ShareStatus] = mapped_column(
        pg_enum(ShareStatus, "share_status_enum"),
        nullable=False,
        server_default=text("'active'"),
    )
    share_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'public'"),
    )
    permission_role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'viewer'"),
    )
    allow_preview: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    allow_download: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    allow_save: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    allow_reshare: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    require_login: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    max_visits: Mapped[int | None] = mapped_column(Integer)
    max_downloads: Mapped[int | None] = mapped_column(Integer)
    password_hash: Mapped[str | None] = mapped_column(String(255))
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
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime)
    expire_time: Mapped[datetime | None] = mapped_column(DateTime)
    visit_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class ShareMember(Base):
    __tablename__ = "share_member"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(user_id, group_id) = 1",
            name="chk_share_member_subject_exactly_one",
        ),
        Index(
            "uk_share_member_user",
            "share_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index(
            "uk_share_member_group",
            "share_id",
            "group_id",
            unique=True,
            postgresql_where=text("group_id IS NOT NULL"),
        ),
        Index("idx_share_member_share_status", "share_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    share_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("share.share_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
    )
    group_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user_group.id", ondelete="CASCADE"),
    )
    status: Mapped[ShareMemberStatus] = mapped_column(
        pg_enum(ShareMemberStatus, "share_member_status_enum"),
        nullable=False,
        server_default=text("'pending'"),
    )
    target_folder_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("folder.folder_id", ondelete="SET NULL"),
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime)
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


class FavoriteItem(Base):
    __tablename__ = "favorite_item"
    __table_args__ = (
        CheckConstraint("num_nonnulls(file_id, folder_id) = 1", name="chk_favorite_item_target_exactly_one"),
        CheckConstraint(
            "(item_type = 'file' AND file_id IS NOT NULL AND folder_id IS NULL) OR "
            "(item_type = 'folder' AND folder_id IS NOT NULL AND file_id IS NULL)",
            name="chk_favorite_item_type_match",
        ),
        Index(
            "uk_favorite_item_file",
            "user_id",
            "file_id",
            unique=True,
            postgresql_where=text("file_id IS NOT NULL"),
        ),
        Index(
            "uk_favorite_item_folder",
            "user_id",
            "folder_id",
            unique=True,
            postgresql_where=text("folder_id IS NOT NULL"),
        ),
    )

    favorite_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    item_type: Mapped[FavoriteItemType] = mapped_column(
        pg_enum(FavoriteItemType, "favorite_item_type_enum"),
        nullable=False,
    )
    file_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("file.file_id", ondelete="CASCADE"),
    )
    folder_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("folder.folder_id", ondelete="CASCADE"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class UserFolderPreference(Base):
    __tablename__ = "user_folder_preference"
    __table_args__ = (
        Index(
            "uk_user_folder_preference_default",
            "user_id",
            unique=True,
            postgresql_where=text("folder_id IS NULL"),
        ),
        Index(
            "uk_user_folder_preference_folder",
            "user_id",
            "folder_id",
            unique=True,
            postgresql_where=text("folder_id IS NOT NULL"),
        ),
    )

    preference_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    folder_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("folder.folder_id", ondelete="CASCADE"),
    )
    view_mode: Mapped[ViewMode] = mapped_column(
        pg_enum(ViewMode, "view_mode_enum"),
        nullable=False,
        server_default=text("'list'"),
    )
    sort_by: Mapped[SortBy] = mapped_column(
        pg_enum(SortBy, "sort_by_enum"),
        nullable=False,
        server_default=text("'name'"),
    )
    sort_direction: Mapped[SortDirection] = mapped_column(
        pg_enum(SortDirection, "sort_direction_enum"),
        nullable=False,
        server_default=text("'asc'"),
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


class ShareAccessLog(Base):
    __tablename__ = "share_access_log"
    __table_args__ = (
        Index("idx_share_access_log_share_created_at", "share_id", text("created_at DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    share_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("share.share_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="SET NULL"),
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    result: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'success'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


__all__ = [
    "Acl",
    "FavoriteItem",
    "Share",
    "ShareAccessLog",
    "ShareMember",
    "UserFolderPreference",
]
