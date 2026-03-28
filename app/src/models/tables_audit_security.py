from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .enums import ScanResult
from .pg import pg_enum


class Log(Base):
    __tablename__ = "log"
    __table_args__ = (
        Index("idx_log_performed_at", "performed_at"),
        Index("idx_log_user_operation", "user_id", "operation"),
        Index("idx_log_target", "target_type", "target_id"),
        Index("idx_log_request_id", "request_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="SET NULL"),
    )
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'user'"))
    operation: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[int | None] = mapped_column(BigInteger)
    result: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'success'"))
    request_id: Mapped[str | None] = mapped_column(String(128))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    details: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    performed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class Notification(Base):
    __tablename__ = "notification"
    __table_args__ = (
        Index("idx_notification_user_status", "user_id", "status", "is_read"),
        Index("idx_notification_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(255))
    notification_type: Mapped[str] = mapped_column(
        "type",
        String(50),
        nullable=False,
        server_default=text("'system'"),
    )
    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'in_app'"),
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_read: Mapped[bool | None] = mapped_column(Boolean, server_default=text("FALSE"))
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'pending'"))
    sender_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class ObjectScanResult(Base):
    __tablename__ = "object_scan_result"
    __table_args__ = (
        Index("idx_object_scan_result_object_scanned_at", "object_id", text("scanned_at DESC")),
    )

    scan_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    object_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("storage_object.object_id", ondelete="CASCADE"),
        nullable=False,
    )
    scan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    engine_name: Mapped[str | None] = mapped_column(String(100))
    engine_version: Mapped[str | None] = mapped_column(String(100))
    result: Mapped[ScanResult] = mapped_column(
        pg_enum(ScanResult, "scan_result_enum"),
        nullable=False,
        server_default=text("'pending'"),
    )
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class ModerationCase(Base):
    __tablename__ = "moderation_case"
    __table_args__ = (
        Index("idx_moderation_case_status_created_at", "status", text("created_at DESC")),
    )

    case_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    object_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("storage_object.object_id", ondelete="CASCADE"),
        nullable=False,
    )
    file_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("file.file_id", ondelete="SET NULL"),
    )
    reason_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'pending'"))
    resolution: Mapped[str | None] = mapped_column(String(50))
    detail: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
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
    handled_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="SET NULL"),
    )
    handled_at: Mapped[datetime | None] = mapped_column(DateTime)


class SecurityEvent(Base):
    __tablename__ = "security_event"
    __table_args__ = (
        Index("idx_security_event_user_occurred_at", "user_id", text("occurred_at DESC")),
        Index("idx_security_event_type_occurred_at", "event_type", text("occurred_at DESC")),
    )

    event_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="SET NULL"),
    )
    session_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user_session.session_id", ondelete="SET NULL"),
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'info'"))
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[int | None] = mapped_column(BigInteger)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    detail: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


__all__ = [
    "Log",
    "ModerationCase",
    "Notification",
    "ObjectScanResult",
    "SecurityEvent",
]
