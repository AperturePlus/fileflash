from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.enums import FileStatus, FolderStatus
from ..models.tables_identity import User
from ..models.tables_storage import File, Folder
from ..schemas.user import BreakdownDetail, StorageStats


class StorageService:
    def __init__(self, *, db: AsyncSession) -> None:
        self.db = db

    async def get_summary(self, *, current_user: User) -> StorageStats:
        file_count = await self.db.scalar(
            select(func.count()).select_from(File).where(and_(File.owner_id == current_user.user_id, File.status == FileStatus.ACTIVE))
        )
        folder_count = await self.db.scalar(
            select(func.count()).select_from(Folder).where(and_(Folder.owner_id == current_user.user_id, Folder.status == FolderStatus.ACTIVE))
        )
        used = await self.db.scalar(
            select(func.coalesce(func.sum(File.file_size), 0)).where(and_(File.owner_id == current_user.user_id, File.status == FileStatus.ACTIVE))
        )

        storage_used = int(used or 0)
        storage_limit = int(current_user.storage_limit or 0)
        storage_available = max(0, storage_limit - storage_used)
        storage_percentage = (storage_used / storage_limit * 100.0) if storage_limit > 0 else 0.0

        # Minimal breakdown: everything goes into "all"
        breakdown = {"all": BreakdownDetail(size=storage_used, count=int(file_count or 0))}

        return StorageStats(
            storage_limit=storage_limit,
            storage_used=storage_used,
            storage_available=storage_available,
            storage_percentage=storage_percentage,
            file_count=int(file_count or 0),
            folder_count=int(folder_count or 0),
            breakdown=breakdown,
        )

