from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...models.enums import FileStatus, ScanResult
from ...models.tables_audit_security import ObjectScanResult
from ...models.tables_identity import User
from ...models.tables_storage import File, StorageObject
from ...schemas.admin.files import AdminFileAuditItem, ListAdminFilesQuery, RescanResponse, VirusStatus
from ...schemas.common import PaginatedData, PaginationMeta


class EventPublisherProtocol(Protocol):
    async def publish(self, event_name: str, payload: dict[str, Any]) -> None: ...


_VIRUS_STATUS_MAP: dict[ScanResult, VirusStatus] = {
    ScanResult.CLEAN: "clean",
    ScanResult.PENDING: "pending",
    ScanResult.INFECTED: "flagged",
    ScanResult.BLOCKED: "flagged",
    ScanResult.FAILED: "pending",
}


class AdminFilesService:
    def __init__(self, db: AsyncSession, publisher: EventPublisherProtocol) -> None:
        self.db = db
        self.publisher = publisher

    async def list_files(self, *, query: ListAdminFilesQuery) -> PaginatedData[AdminFileAuditItem]:
        latest_scan = (
            select(ObjectScanResult.object_id, func.max(ObjectScanResult.scanned_at).label("scanned_at"))
            .group_by(ObjectScanResult.object_id)
            .subquery()
        )
        statement = (
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

        sort_column = {
            "name": File.file_name,
            "size": File.file_size,
            "createdAt": File.created_at,
            "updatedAt": File.updated_at,
        }[query.sort]
        statement = statement.order_by(sort_column.desc() if query.order == "desc" else sort_column.asc())

        total = int(await self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        total_pages = max(1, -(-total // query.per_page))
        offset = (query.page - 1) * query.per_page
        rows = (await self.db.execute(statement.offset(offset).limit(query.per_page))).all()
        items = [self._to_item(file_row, object_row, owner_row, scan_row) for file_row, object_row, owner_row, scan_row in rows]
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

    @staticmethod
    def _to_item(
        file_row: File,
        object_row: StorageObject,
        owner_row: User,
        scan_row: ObjectScanResult | None,
    ) -> AdminFileAuditItem:
        return AdminFileAuditItem(
            id=str(file_row.file_id),
            name=file_row.file_name,
            size=int(file_row.file_size),
            mime_type=file_row.mime_type or object_row.content_type or "application/octet-stream",
            hash=(object_row.object_hash or "")[:16],
            virus_status=_VIRUS_STATUS_MAP.get(scan_row.result, "pending") if scan_row else "pending",
            is_shared=False,
            owner_name=owner_row.username,
            updated_at=file_row.updated_at,
            created_at=file_row.created_at,
        )


__all__ = ["AdminFilesService"]
