from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..models.enums import FavoriteItemType, FileStatus, FolderStatus, FolderType
from ..models.tables_access_share import FavoriteItem
from ..models.tables_identity import User
from ..models.tables_storage import File, Folder
from ..schemas.common import PaginatedData, PaginationMeta
from ..schemas.file import ContentItem, FileDetails, FileItem, GetFilesQuery

_SORT_COLUMNS = {
    "name": File.file_name,
    "size": File.file_size,
    "createdAt": File.created_at,
    "updatedAt": File.updated_at,
}


class FileService:
    def __init__(self, *, db: AsyncSession) -> None:
        self.db = db

    async def list_files(self, *, user_id: int, query: GetFilesQuery) -> PaginatedData[FileItem]:
        folder_id = await self._resolve_folder_id(user_id, query.folder_id)

        base = (
            select(File, User.username)
            .join(User, User.user_id == File.owner_id)
            .where(
                and_(
                    File.owner_id == user_id,
                    File.folder_id == folder_id,
                    File.status == FileStatus.ACTIVE,
                    File.is_latest.is_(True),
                )
            )
        )

        if query.search:
            base = base.where(func.lower(File.file_name).contains(query.search.lower()))
        if query.mime_type:
            base = base.where(File.mime_type == query.mime_type)

        total = await self.db.scalar(select(func.count()).select_from(base.subquery()))
        total = total or 0

        col = _SORT_COLUMNS.get(query.sort or "name", File.file_name)
        base = base.order_by(col.desc() if query.order == "desc" else col.asc())

        per_page = query.per_page
        offset = (query.page - 1) * per_page
        rows = (await self.db.execute(base.offset(offset).limit(per_page))).all()

        starred_ids = await self._starred_file_ids(user_id, [r[0].file_id for r in rows])

        items = [self._to_file_item(f, username, f.file_id in starred_ids) for f, username in rows]
        return self._paginate(items, total, query.page, per_page)

    async def get_file(self, *, user_id: int, file_id: int) -> FileDetails:
        row = (
            await self.db.execute(
                select(File, User.username)
                .join(User, User.user_id == File.owner_id)
                .where(
                    and_(
                        File.file_id == file_id,
                        File.owner_id == user_id,
                        File.status == FileStatus.ACTIVE,
                    )
                )
            )
        ).first()

        if row is None:
            raise ApiError(status_code=404, code=404, message="File not found")

        f, username = row
        is_starred = await self._is_file_starred(user_id, file_id)
        return FileDetails(
            id=str(f.file_id),
            name=f.file_name,
            size=f.file_size,
            mime_type=f.mime_type or "application/octet-stream",
            owner_name=username,
            updated_at=f.updated_at,
            created_at=f.created_at,
            folder_id=str(f.folder_id),
            permission="owner",
            is_starred=is_starred,
            status=True,
        )

    async def list_starred(self, *, user_id: int) -> PaginatedData[ContentItem]:
        # starred files
        file_rows = (
            await self.db.execute(
                select(File, User.username)
                .join(User, User.user_id == File.owner_id)
                .join(
                    FavoriteItem,
                    and_(
                        FavoriteItem.file_id == File.file_id,
                        FavoriteItem.user_id == user_id,
                    ),
                )
                .where(and_(File.owner_id == user_id, File.status == FileStatus.ACTIVE))
            )
        ).all()

        # starred folders
        folder_rows = (
            await self.db.execute(
                select(Folder, User.username)
                .join(User, User.user_id == Folder.owner_id)
                .join(
                    FavoriteItem,
                    and_(
                        FavoriteItem.folder_id == Folder.folder_id,
                        FavoriteItem.user_id == user_id,
                    ),
                )
                .where(and_(Folder.owner_id == user_id, Folder.status == FolderStatus.ACTIVE))
            )
        ).all()

        items: list[ContentItem] = []
        for f, username in file_rows:
            items.append(self._to_file_item(f, username, is_starred=True))
        for folder, username in folder_rows:
            items.append(self._to_folder_item(folder, username, is_starred=True))

        return self._paginate(items, len(items), 1, max(len(items), 1))

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    async def _resolve_folder_id(self, user_id: int, folder_id_str: str | None) -> int:
        if not folder_id_str or folder_id_str == "root":
            folder = await self.db.scalar(
                select(Folder).where(
                    and_(
                        Folder.owner_id == user_id,
                        Folder.parent_folder_id.is_(None),
                        Folder.folder_type == FolderType.ROOT,
                        Folder.status == FolderStatus.ACTIVE,
                    )
                )
            )
            if folder is None:
                raise ApiError(status_code=404, code=404, message="Root folder not found")
            return folder.folder_id

        try:
            fid = int(folder_id_str)
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message="Invalid folderId") from exc

        exists = await self.db.scalar(
            select(Folder.folder_id).where(
                and_(Folder.folder_id == fid, Folder.owner_id == user_id, Folder.status == FolderStatus.ACTIVE)
            )
        )
        if exists is None:
            raise ApiError(status_code=404, code=404, message="Folder not found")
        return fid

    async def _starred_file_ids(self, user_id: int, file_ids: list[int]) -> set[int]:
        if not file_ids:
            return set()
        rows = await self.db.scalars(
            select(FavoriteItem.file_id).where(
                and_(
                    FavoriteItem.user_id == user_id,
                    FavoriteItem.item_type == FavoriteItemType.FILE,
                    FavoriteItem.file_id.in_(file_ids),
                )
            )
        )
        return set(rows)

    async def _is_file_starred(self, user_id: int, file_id: int) -> bool:
        return (
            await self.db.scalar(
                select(FavoriteItem.favorite_id).where(
                    and_(
                        FavoriteItem.user_id == user_id,
                        FavoriteItem.file_id == file_id,
                    )
                )
            )
        ) is not None

    @staticmethod
    def _to_file_item(f: File, owner_name: str, is_starred: bool) -> FileItem:
        return FileItem(
            id=str(f.file_id),
            name=f.file_name,
            size=f.file_size,
            mime_type=f.mime_type or "application/octet-stream",
            owner_name=owner_name,
            updated_at=f.updated_at,
            created_at=f.created_at,
            folder_id=str(f.folder_id),
            permission="owner",
            is_starred=is_starred,
        )

    @staticmethod
    def _to_folder_item(folder: Folder, owner_name: str, is_starred: bool) -> ContentItem:
        from ..schemas.file import FolderItem

        return FolderItem(
            id=str(folder.folder_id),
            name=folder.folder_name,
            size=folder.cached_size,
            owner_name=owner_name,
            updated_at=folder.updated_at,
            created_at=folder.created_at,
            parent_folder_id=str(folder.parent_folder_id) if folder.parent_folder_id else None,
            permission="owner",
            is_starred=is_starred,
        )

    @staticmethod
    def _paginate(items: list, total: int, page: int, per_page: int) -> PaginatedData:
        total_pages = max(1, -(-total // per_page))
        return PaginatedData(
            items=items,
            pagination=PaginationMeta(
                total_items=total,
                total_pages=total_pages,
                per_page=per_page,
                current_page=page,
                has_prev=page > 1,
                has_next=page < total_pages,
            ),
        )
