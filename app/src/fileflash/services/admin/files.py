from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...core.http_headers import build_content_disposition
from ...core.mime import DEFAULT_MIME_TYPE, resolve_file_mime_type
from ...models.enums import FileStatus, ScanResult, ShareStatus, UploadStatus
from ...models.tables_access_share import Share
from ...models.tables_audit_security import ObjectScanResult
from ...models.tables_identity import User
from ...models.tables_storage import File, FileMediaMetadata, StorageObject
from ...s3.minio_client import MinioObjectStorageClient
from ...schemas.admin.files import (
    AdminFileAuditDetail,
    AdminFileAuditItem,
    AdminFileAuditOwner,
    AdminFileLatestScan,
    ListAdminFilesQuery,
    RescanResponse,
    VirusStatus,
)
from ...schemas.common import PaginatedData, PaginationMeta


class EventPublisherProtocol(Protocol):
    async def publish(self, event_name: str, payload: dict[str, Any]) -> None: ...


@dataclass(slots=True)
class AdminFileStreamResult:
    stream: AsyncIterator[bytes]
    filename: str
    content_type: str
    status_code: int
    headers: dict[str, str]


@dataclass(slots=True)
class ResolvedAdminStreamObject:
    storage_object: StorageObject
    content_type_override: str | None = None


_VIRUS_STATUS_MAP: dict[ScanResult, VirusStatus] = {
    ScanResult.CLEAN: "clean",
    ScanResult.PENDING: "pending",
    ScanResult.INFECTED: "flagged",
    ScanResult.BLOCKED: "flagged",
    ScanResult.FAILED: "pending",
}

TRANSCODE_READY_STATUS = "ready"


class AdminFilesService:
    def __init__(
        self,
        db: AsyncSession,
        publisher: EventPublisherProtocol,
        storage: MinioObjectStorageClient | None = None,
    ) -> None:
        self.db = db
        self.publisher = publisher
        self.storage = storage

    async def list_files(self, *, query: ListAdminFilesQuery) -> PaginatedData[AdminFileAuditItem]:
        latest_scan = self._latest_scan_subquery()
        object_stats = self._object_stats_subquery()
        share_stats = self._share_stats_subquery()

        statement = (
            select(
                File,
                StorageObject,
                User,
                ObjectScanResult,
                object_stats.c.upload_count,
                object_stats.c.owner_count,
                share_stats.c.share_count,
            )
            .join(StorageObject, File.storage_object_id == StorageObject.object_id)
            .join(User, File.owner_id == User.user_id)
            .join(object_stats, object_stats.c.object_id == StorageObject.object_id, isouter=True)
            .join(share_stats, share_stats.c.object_id == StorageObject.object_id, isouter=True)
            .join(latest_scan, latest_scan.c.object_id == StorageObject.object_id, isouter=True)
            .join(
                ObjectScanResult,
                and_(
                    ObjectScanResult.object_id == latest_scan.c.object_id,
                    ObjectScanResult.scanned_at == latest_scan.c.scanned_at,
                ),
                isouter=True,
            )
            .where(File.status == FileStatus.ACTIVE)
            .where(File.deleted_at.is_(None))
        )

        if query.search:
            kw = f"%{query.search.strip().lower()}%"
            statement = statement.where(func.lower(File.file_name).like(kw))
        if query.owner_id:
            statement = statement.where(File.owner_id == int(query.owner_id))
        if query.mime_type:
            statement = statement.where(File.mime_type == query.mime_type)
        if query.virus_status:
            wanted = [raw for raw, mapped in _VIRUS_STATUS_MAP.items() if mapped == query.virus_status]
            statement = statement.where(ObjectScanResult.result.in_(wanted))

        total = int(await self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0)

        sort_column = {
            "name": File.file_name,
            "size": File.file_size,
            "createdAt": File.created_at,
            "updatedAt": File.updated_at,
        }[query.sort]
        statement = statement.order_by(sort_column.desc() if query.order == "desc" else sort_column.asc())

        total_pages = max(1, -(-total // query.per_page))
        offset = (query.page - 1) * query.per_page
        rows = (await self.db.execute(statement.offset(offset).limit(query.per_page))).all()
        items = [
            self._to_item(
                file_row,
                object_row,
                owner_row,
                scan_row,
                upload_count=upload_count,
                owner_count=owner_count,
                share_count=share_count,
            )
            for (
                file_row,
                object_row,
                owner_row,
                scan_row,
                upload_count,
                owner_count,
                share_count,
            ) in rows
        ]
        return PaginatedData(
            items=items,
            pagination=PaginationMeta(
                total_items=total,
                total_pages=total_pages,
                per_page=query.per_page,
                current_page=query.page,
                has_prev=query.page > 1,
                has_next=query.page < total_pages,
            ),
        )

    async def get_file_detail(self, *, file_id: int) -> AdminFileAuditDetail:
        file_row, object_row, owner_row, scan_row = await self._get_active_file_context(file_id=file_id)
        owners = await self._load_object_owners(object_id=int(object_row.object_id))
        upload_count = sum(owner.file_count for owner in owners)
        owner_count = len(owners)
        is_shared = await self._object_is_shared(object_id=int(object_row.object_id))

        item = self._to_item(
            file_row,
            object_row,
            owner_row,
            scan_row,
            upload_count=upload_count,
            owner_count=owner_count,
            share_count=1 if is_shared else 0,
        )
        return AdminFileAuditDetail(
            **item.model_dump(),
            object_hash=object_row.object_hash,
            hash_algorithm=object_row.hash_algorithm,
            storage_status=self._enum_value(object_row.upload_status),
            latest_scan=self._to_latest_scan(scan_row),
            owners=owners,
        )

    async def get_preview_stream(
        self,
        *,
        file_id: int,
        range_header: str | None,
    ) -> AdminFileStreamResult:
        if self.storage is None:
            raise ApiError(status_code=503, code=503, message="Object storage is unavailable")

        file_row, object_row, _owner_row, _scan_row = await self._get_active_file_context(file_id=file_id)
        resolved_object = await self._resolve_stream_storage_object(
            file_row=file_row,
            source_object=object_row,
            prefer_optimized=True,
        )
        storage_object = resolved_object.storage_object if resolved_object is not None else None
        if storage_object is None or not self._is_upload_status_active(storage_object.upload_status):
            raise ApiError(status_code=404, code=404, message="File content not found")

        object_size = int(storage_object.object_size or file_row.file_size or 0)
        if object_size <= 0:
            raise ApiError(status_code=404, code=404, message="File content not found")

        content_type = resolve_file_mime_type(
            mime_type=(
                resolved_object.content_type_override
                if resolved_object is not None and resolved_object.content_type_override
                else file_row.mime_type or storage_object.content_type
            ),
            file_ext=file_row.file_ext,
            file_name=file_row.file_name,
            default=DEFAULT_MIME_TYPE,
        )
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": build_content_disposition(file_row.file_name, disposition="inline"),
        }

        byte_range = self._parse_range_header(range_header=range_header, file_size=object_size)
        if byte_range is None:
            headers["Content-Length"] = str(object_size)
            stream = self.storage.iter_object(
                bucket_name=storage_object.bucket_name,
                object_key=storage_object.object_key,
            )
            return AdminFileStreamResult(
                stream=stream,
                filename=file_row.file_name,
                content_type=content_type,
                status_code=200,
                headers=headers,
            )

        start, end = byte_range
        headers["Content-Length"] = str(end - start + 1)
        headers["Content-Range"] = f"bytes {start}-{end}/{object_size}"
        stream = self.storage.iter_object_range(
            bucket_name=storage_object.bucket_name,
            object_key=storage_object.object_key,
            start=start,
            end=end,
        )
        return AdminFileStreamResult(
            stream=stream,
            filename=file_row.file_name,
            content_type=content_type,
            status_code=206,
            headers=headers,
        )

    async def request_rescan(self, *, file_id: int, requested_by: int) -> RescanResponse:
        file_row = await self.db.get(File, file_id)
        if file_row is None or file_row.deleted_at is not None or file_row.status != FileStatus.ACTIVE:
            raise ApiError(status_code=404, code=404, message="File not found")

        now = datetime.now(UTC)
        self.db.add(
            ObjectScanResult(
                object_id=int(file_row.storage_object_id),
                scan_type="virus",
                result=ScanResult.PENDING,
                details={"requestedBy": requested_by},
                scanned_at=now,
                created_at=now,
            )
        )
        await self.db.commit()

        await self.publisher.publish(
            "files.rescan_requested",
            {
                "fileId": str(file_id),
                "objectId": str(file_row.storage_object_id),
                "requestedBy": requested_by,
            },
        )
        return RescanResponse(file_id=str(file_id), virus_status="pending", scanned_at=now)

    async def _get_active_file_context(
        self,
        *,
        file_id: int,
    ) -> tuple[File, StorageObject, User, ObjectScanResult | None]:
        latest_scan = self._latest_scan_subquery()
        row = (
            await self.db.execute(
                select(File, StorageObject, User, ObjectScanResult)
                .join(StorageObject, File.storage_object_id == StorageObject.object_id)
                .join(User, File.owner_id == User.user_id)
                .join(latest_scan, latest_scan.c.object_id == StorageObject.object_id, isouter=True)
                .join(
                    ObjectScanResult,
                    and_(
                        ObjectScanResult.object_id == latest_scan.c.object_id,
                        ObjectScanResult.scanned_at == latest_scan.c.scanned_at,
                    ),
                    isouter=True,
                )
                .where(File.file_id == file_id)
                .where(File.status == FileStatus.ACTIVE)
                .where(File.deleted_at.is_(None))
            )
        ).first()
        if row is None:
            raise ApiError(status_code=404, code=404, message="File not found")
        file_row, object_row, owner_row, scan_row = row
        return file_row, object_row, owner_row, scan_row

    async def _load_object_owners(self, *, object_id: int) -> list[AdminFileAuditOwner]:
        first_uploaded = func.min(File.created_at)
        last_uploaded = func.max(File.created_at)
        rows = (
            await self.db.execute(
                select(
                    User.user_id,
                    User.username,
                    User.email,
                    func.count(File.file_id),
                    first_uploaded,
                    last_uploaded,
                )
                .join(User, User.user_id == File.owner_id)
                .where(File.storage_object_id == object_id)
                .where(File.status == FileStatus.ACTIVE)
                .where(File.deleted_at.is_(None))
                .group_by(User.user_id, User.username, User.email)
                .order_by(last_uploaded.desc())
            )
        ).all()
        return [
            AdminFileAuditOwner(
                user_id=str(user_id),
                username=username,
                email=email,
                file_count=int(file_count or 0),
                first_uploaded_at=first_uploaded_at,
                last_uploaded_at=last_uploaded_at,
            )
            for user_id, username, email, file_count, first_uploaded_at, last_uploaded_at in rows
        ]

    async def _object_is_shared(self, *, object_id: int) -> bool:
        now = datetime.now(UTC)
        share_id = await self.db.scalar(
            select(Share.share_id)
            .join(File, File.file_id == Share.file_id)
            .where(File.storage_object_id == object_id)
            .where(File.status == FileStatus.ACTIVE)
            .where(File.deleted_at.is_(None))
            .where(Share.status == ShareStatus.ACTIVE)
            .where(or_(Share.expire_time.is_(None), Share.expire_time > now))
            .limit(1)
        )
        return share_id is not None

    async def _resolve_stream_storage_object(
        self,
        *,
        file_row: File,
        source_object: StorageObject,
        prefer_optimized: bool,
    ) -> ResolvedAdminStreamObject | None:
        if not prefer_optimized:
            return ResolvedAdminStreamObject(storage_object=source_object)

        metadata_row = await self.db.scalar(
            select(FileMediaMetadata)
            .where(FileMediaMetadata.source_object_id == int(file_row.storage_object_id))
            .limit(1)
        )
        if not isinstance(metadata_row, FileMediaMetadata):
            return ResolvedAdminStreamObject(storage_object=source_object)
        transcode = (metadata_row.extra_metadata or {}).get("transcode")
        if not isinstance(transcode, dict):
            return ResolvedAdminStreamObject(storage_object=source_object)
        if str(transcode.get("status") or "").strip().lower() != TRANSCODE_READY_STATUS:
            return ResolvedAdminStreamObject(storage_object=source_object)

        bucket_name = str(transcode.get("optimizedBucketName") or "").strip()
        object_key = str(transcode.get("optimizedObjectKey") or "").strip()
        if not bucket_name or not object_key:
            return ResolvedAdminStreamObject(storage_object=source_object)

        optimized_mime_type = str(transcode.get("optimizedMimeType") or "").strip() or None
        optimized_object = await self.db.scalar(
            select(StorageObject)
            .where(
                and_(
                    StorageObject.bucket_name == bucket_name,
                    StorageObject.object_key == object_key,
                    StorageObject.upload_status == UploadStatus.ACTIVE,
                )
            )
            .limit(1)
        )
        if isinstance(optimized_object, StorageObject):
            return ResolvedAdminStreamObject(
                storage_object=optimized_object,
                content_type_override=optimized_mime_type or optimized_object.content_type,
            )

        if self.storage is None:
            return ResolvedAdminStreamObject(storage_object=source_object)
        exists = await self.storage.object_exists(bucket_name=bucket_name, object_key=object_key)
        if not exists:
            return ResolvedAdminStreamObject(storage_object=source_object)

        stat = await self.storage.stat_object(bucket_name=bucket_name, object_key=object_key)
        created = StorageObject(
            bucket_name=bucket_name,
            object_key=object_key,
            object_size=int(stat.size),
            etag=stat.etag,
            version_id=stat.version_id,
            content_type=stat.content_type,
            upload_status=UploadStatus.ACTIVE,
        )
        self.db.add(created)
        await self.db.flush()
        return ResolvedAdminStreamObject(
            storage_object=created,
            content_type_override=optimized_mime_type or created.content_type,
        )

    @staticmethod
    def _latest_scan_subquery():
        return (
            select(ObjectScanResult.object_id, func.max(ObjectScanResult.scanned_at).label("scanned_at"))
            .group_by(ObjectScanResult.object_id)
            .subquery()
        )

    @staticmethod
    def _object_stats_subquery():
        return (
            select(
                File.storage_object_id.label("object_id"),
                func.count(File.file_id).label("upload_count"),
                func.count(func.distinct(File.owner_id)).label("owner_count"),
            )
            .where(File.status == FileStatus.ACTIVE)
            .where(File.deleted_at.is_(None))
            .group_by(File.storage_object_id)
            .subquery()
        )

    @staticmethod
    def _share_stats_subquery():
        now = datetime.now(UTC)
        return (
            select(
                File.storage_object_id.label("object_id"),
                func.count(Share.share_id).label("share_count"),
            )
            .join(Share, Share.file_id == File.file_id)
            .where(File.status == FileStatus.ACTIVE)
            .where(File.deleted_at.is_(None))
            .where(Share.status == ShareStatus.ACTIVE)
            .where(or_(Share.expire_time.is_(None), Share.expire_time > now))
            .group_by(File.storage_object_id)
            .subquery()
        )

    @staticmethod
    def _to_item(
        file_row: File,
        object_row: StorageObject,
        owner_row: User,
        scan_row: ObjectScanResult | None,
        *,
        upload_count: int | None,
        owner_count: int | None,
        share_count: int | None,
    ) -> AdminFileAuditItem:
        return AdminFileAuditItem(
            id=str(file_row.file_id),
            object_id=str(object_row.object_id),
            name=file_row.file_name,
            size=int(file_row.file_size),
            mime_type=file_row.mime_type or object_row.content_type or DEFAULT_MIME_TYPE,
            hash=(object_row.object_hash or "")[:16],
            virus_status=_VIRUS_STATUS_MAP.get(scan_row.result, "pending") if scan_row else "pending",
            is_shared=bool(share_count or 0),
            owner_name=owner_row.username,
            upload_count=int(upload_count or 1),
            owner_count=int(owner_count or 1),
            scanned_at=scan_row.scanned_at if scan_row else None,
            updated_at=file_row.updated_at,
            created_at=file_row.created_at,
        )

    @staticmethod
    def _to_latest_scan(scan_row: ObjectScanResult | None) -> AdminFileLatestScan | None:
        if scan_row is None:
            return None
        result = AdminFilesService._enum_value(scan_row.result)
        return AdminFileLatestScan(
            scan_type=scan_row.scan_type,
            scan_result=result,
            virus_status=_VIRUS_STATUS_MAP.get(scan_row.result, "pending"),
            scanned_at=scan_row.scanned_at,
            details=scan_row.details,
        )

    @staticmethod
    def _enum_value(value: object) -> str:
        return str(getattr(value, "value", value))

    @staticmethod
    def _is_upload_status_active(value: object) -> bool:
        return value == UploadStatus.ACTIVE or AdminFilesService._enum_value(value) == UploadStatus.ACTIVE.value

    @staticmethod
    def _parse_range_header(range_header: str | None, file_size: int) -> tuple[int, int] | None:
        if not range_header:
            return None

        value = range_header.strip()
        if not value.lower().startswith("bytes="):
            raise ApiError(status_code=416, code=416, message="Invalid Range header")

        spec = value[6:].strip()
        if "," in spec:
            raise ApiError(status_code=416, code=416, message="Multiple ranges are not supported")

        if spec.startswith("-"):
            suffix_part = spec[1:].strip()
            if not suffix_part.isdigit():
                raise ApiError(status_code=416, code=416, message="Invalid Range header")
            suffix = int(suffix_part)
            if suffix <= 0:
                raise ApiError(status_code=416, code=416, message="Invalid Range header")
            start = max(file_size - suffix, 0)
            end = file_size - 1
            return start, end

        if "-" not in spec:
            raise ApiError(status_code=416, code=416, message="Invalid Range header")

        start_part, end_part = spec.split("-", 1)
        if not start_part.strip().isdigit():
            raise ApiError(status_code=416, code=416, message="Invalid Range header")
        start = int(start_part.strip())
        end = file_size - 1
        if end_part.strip():
            if not end_part.strip().isdigit():
                raise ApiError(status_code=416, code=416, message="Invalid Range header")
            end = int(end_part.strip())

        if start < 0 or start >= file_size or end < start:
            raise ApiError(status_code=416, code=416, message="Requested range is not satisfiable")

        if end >= file_size:
            end = file_size - 1
        return start, end


__all__ = ["AdminFilesService", "AdminFileStreamResult"]
