from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.enums import FileStatus, FolderStatus
from ..models.tables_identity import User
from ..models.tables_storage import File, Folder
from ..schemas.common import PaginatedData, PaginationMeta
from ..schemas.recycle import GetRecycleBinQuery, RecycleBinItem


class RecycleBinService:
    def __init__(self, *, db: AsyncSession) -> None:
        self.db = db

    async def list_items(self, *, current_user: User, query: GetRecycleBinQuery) -> PaginatedData[RecycleBinItem]:
        # Minimal implementation: list deleted files/folders for current user.
        # Auto delete in 30 days (demo rule); can be made configurable later.
        now = datetime.utcnow()
        auto_delete_at = now + timedelta(days=30)

        items: list[RecycleBinItem] = []

        if query.item_type in (None, "folder"):
            folders = list(
                await self.db.scalars(
                    select(Folder).where(
                        and_(
                            Folder.owner_id == current_user.user_id,
                            Folder.status == FolderStatus.DELETED,
                        )
                    )
                )
            )
            for f in folders:
                deleted_at = f.deleted_at or f.updated_at or f.created_at
                items.append(
                    RecycleBinItem(
                        item_type="folder",
                        id=str(f.folder_id),
                        name=f.folder_name,
                        original_path=f"/{f.folder_name}",
                        size=int(f.cached_size or 0),
                        mime_type=None,
                        folder_id=str(f.parent_folder_id) if f.parent_folder_id is not None else None,
                        folder_name=None,
                        deleted_at=deleted_at,
                        auto_delete_at=auto_delete_at,
                        days_until_permanent_delete=30,
                        can_restore=True,
                        restore_conflicts=False,
                    )
                )

        if query.item_type in (None, "file"):
            files = list(
                await self.db.scalars(
                    select(File).where(
                        and_(
                            File.owner_id == current_user.user_id,
                            File.status == FileStatus.DELETED,
                        )
                    )
                )
            )
            for fi in files:
                deleted_at = fi.deleted_at or fi.updated_at or fi.created_at
                items.append(
                    RecycleBinItem(
                        item_type="file",
                        id=str(fi.file_id),
                        name=fi.file_name,
                        original_path=f"/{fi.file_name}",
                        size=int(fi.file_size),
                        mime_type=fi.mime_type,
                        folder_id=str(fi.folder_id),
                        folder_name=None,
                        deleted_at=deleted_at,
                        auto_delete_at=auto_delete_at,
                        days_until_permanent_delete=30,
                        can_restore=True,
                        restore_conflicts=False,
                    )
                )

        # Pagination (in-memory)
        total_items = len(items)
        per_page = query.per_page
        current_page = query.page
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        start = (current_page - 1) * per_page
        end = start + per_page

        page_items = items[start:end]
        pagination = PaginationMeta(
            total_items=total_items,
            total_pages=total_pages,
            per_page=per_page,
            current_page=current_page,
            has_prev=current_page > 1,
            has_next=current_page < total_pages,
        )
        return PaginatedData(items=page_items, pagination=pagination)

