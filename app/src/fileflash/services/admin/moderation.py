from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import ApiError
from ...models.tables_audit_security import ModerationCase
from ...models.tables_storage import File
from ...schemas.admin.moderation import (
    ListViolationsQuery,
    ResolveViolationResponse,
    ViolationItem,
    ViolationLevel,
)
from ...schemas.common import PaginatedData, PaginationMeta

_OPEN_STATES = ("pending", "under_review")


class AdminModerationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_violations(self, *, query: ListViolationsQuery) -> PaginatedData[ViolationItem]:
        statement = select(ModerationCase, File).join(File, File.file_id == ModerationCase.file_id, isouter=True)
        if query.status:
            statement = statement.where(ModerationCase.status == query.status)
        statement = statement.order_by(ModerationCase.created_at.desc())

        total = int(await self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        total_pages = max(1, -(-total // query.per_page))
        offset = (query.page - 1) * query.per_page
        rows = (await self.db.execute(statement.offset(offset).limit(query.per_page))).all()
        items = [self._to_item(case_row, file_row) for case_row, file_row in rows]
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

    async def resolve_case(self, *, case_id: int, handled_by: int) -> ResolveViolationResponse:
        case_row = await self.db.get(ModerationCase, case_id, with_for_update=True)
        if case_row is None:
            raise ApiError(status_code=404, code=404, message="Violation case not found")
        if case_row.status not in _OPEN_STATES:
            raise ApiError(status_code=409, code=409, message="Case already resolved")

        now = datetime.now(UTC)
        case_row.status = "resolved"
        case_row.resolution = "admin_clear"
        case_row.handled_by = handled_by
        case_row.handled_at = now
        case_row.updated_at = now
        await self.db.commit()
        return ResolveViolationResponse(violation_id=str(case_id), resolved_at=now)

    @staticmethod
    def _to_item(case_row: ModerationCase, file_row: File | None) -> ViolationItem:
        return ViolationItem(
            id=str(case_row.case_id),
            file_id=str(case_row.file_id) if case_row.file_id else None,
            file_name=file_row.file_name if file_row else None,
            type=case_row.reason_type,
            level=_level_from_confidence(case_row.confidence),
            reported_at=case_row.created_at,
            status=case_row.status,  # type: ignore[arg-type]
        )


def _level_from_confidence(confidence: Decimal | None) -> ViolationLevel:
    if confidence is None:
        return "low"
    value = float(confidence)
    if value > 0.8:
        return "high"
    if value > 0.5:
        return "medium"
    return "low"


__all__ = ["AdminModerationService"]
