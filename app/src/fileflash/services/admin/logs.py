from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.tables_audit_security import Log
from ...schemas.admin.logs import AdminLogsResponse, ListAdminLogsQuery, LogItem


class AdminLogsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_logs(self, *, query: ListAdminLogsQuery) -> AdminLogsResponse:
        statement = select(Log)
        conditions = []
        if query.user_id:
            conditions.append(Log.user_id == int(query.user_id))
        if query.operation:
            conditions.append(Log.operation == query.operation)
        if query.result:
            conditions.append(Log.result == query.result)
        if query.from_at:
            conditions.append(Log.performed_at >= query.from_at)
        if query.to_at:
            conditions.append(Log.performed_at <= query.to_at)
        if conditions:
            statement = statement.where(and_(*conditions))
        statement = statement.order_by(Log.performed_at.desc(), Log.id.desc())

        total = int(await self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        total_pages = max(1, -(-total // query.per_page))
        offset = (query.page - 1) * query.per_page
        rows = list(await self.db.scalars(statement.offset(offset).limit(query.per_page)))

        logs = [
            LogItem(
                id=str(row.id),
                user_id=str(row.user_id) if row.user_id else None,
                operation=row.operation,
                operation_name=row.operation,
                target_type=row.target_type,
                target_id=str(row.target_id) if row.target_id else None,
                result=row.result,
                ip_address=row.ip_address,
                user_agent=row.user_agent,
                performed_at=row.performed_at or datetime.now(UTC),
                details=row.details,
                metadata=row.metadata_payload or {},
            )
            for row in rows
        ]
        return AdminLogsResponse(
            logs=logs,
            pagination={
                "totalItems": total,
                "totalPages": total_pages,
                "perPage": query.per_page,
                "currentPage": query.page,
                "hasPrev": query.page > 1,
                "hasNext": query.page < total_pages,
            },
        )


__all__ = ["AdminLogsService"]
