from __future__ import annotations

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.enums import FileStatus
from ..models.tables_identity import User
from ..models.tables_storage import File
from ..schemas.common import PaginatedData, PaginationMeta
from ..schemas.file import FileItem, GetFilesQuery


class FileService:
    def __init__(self, *, db: AsyncSession) -> None:
        self.db = db

    async def list_files(self, *, current_user: User, query: GetFilesQuery) -> PaginatedData[FileItem]:
        stmt = select(File).where(and_(File.owner_id == current_user.user_id, File.status == FileStatus.ACTIVE))

        if query.folder_id:
            try:
                folder_id_int = int(query.folder_id)
            except ValueError:
                folder_id_int = None
            if folder_id_int is not None:
                stmt = stmt.where(File.folder_id == folder_id_int)

        if query.search:
            s = query.search.strip().lower()
            stmt = stmt.where(
                or_(
                    func.lower(File.file_name).contains(s),
                    func.lower(func.coalesce(File.mime_type, "")).contains(s),
                )
            )

        # Sorting (minimal set)
        if query.sort == "name":
            order_col = File.file_name
        elif query.sort == "size":
            order_col = File.file_size
        elif query.sort == "updatedAt":
            order_col = File.updated_at
        else:
            order_col = File.created_at

        if query.order == "asc":
            stmt = stmt.order_by(order_col.asc())
        else:
            stmt = stmt.order_by(order_col.desc())

        total_items = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        total_items = int(total_items or 0)

        per_page = query.per_page
        current_page = query.page
        total_pages = max(1, (total_items + per_page - 1) // per_page)

        stmt = stmt.offset((current_page - 1) * per_page).limit(per_page)
        rows = list(await self.db.scalars(stmt))

        items = [
            FileItem(
                id=str(row.file_id),
                name=row.file_name,
                size=int(row.file_size),
                mime_type=row.mime_type or "application/octet-stream",
                owner_name=current_user.username,
                updated_at=row.updated_at,
                created_at=row.created_at,
                folder_id=str(row.folder_id),
                permission="owner",
            )
            for row in rows
        ]

        pagination = PaginationMeta(
            total_items=total_items,
            total_pages=total_pages,
            per_page=per_page,
            current_page=current_page,
            has_prev=current_page > 1,
            has_next=current_page < total_pages,
        )
        return PaginatedData(items=items, pagination=pagination)

