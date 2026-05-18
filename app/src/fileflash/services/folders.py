from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..models.enums import FileStatus, FolderStatus, FolderType
from ..models.tables_identity import User
from ..models.tables_storage import File, Folder
from ..schemas.common import PaginatedData, PaginationMeta
from ..schemas.file import ContentItem, CreateFolderRequest, FileItem, FolderContentsQuery, FolderItem, FolderPathResponse, PathItem


class FolderService:
    def __init__(self, *, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create_root_folder_id(self, *, owner_id: int) -> int:
        folder = await self.db.scalar(
            select(Folder).where(
                and_(
                    Folder.owner_id == owner_id,
                    Folder.parent_folder_id.is_(None),
                    Folder.folder_type == FolderType.ROOT,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if folder is not None:
            return folder.folder_id

        # Create a root folder if missing
        folder = Folder(
            owner_id=owner_id,
            parent_folder_id=None,
            folder_name="My Files",
            status=FolderStatus.ACTIVE,
            folder_type=FolderType.ROOT,
        )
        self.db.add(folder)
        await self.db.flush()
        await self.db.commit()
        return folder.folder_id

    async def create_folder(self, *, current_user: User, payload: CreateFolderRequest) -> FolderItem:
        if payload.parent_folder_id is None:
            parent_id = await self.get_or_create_root_folder_id(owner_id=current_user.user_id)
        elif payload.parent_folder_id == "root":
            parent_id = await self.get_or_create_root_folder_id(owner_id=current_user.user_id)
        else:
            try:
                parent_id = int(payload.parent_folder_id)
            except ValueError as exc:
                raise ApiError(status_code=400, code=400, message="Invalid parentFolderId") from exc

            parent = await self.db.scalar(
                select(Folder).where(
                    and_(
                        Folder.folder_id == parent_id,
                        Folder.owner_id == current_user.user_id,
                        Folder.status == FolderStatus.ACTIVE,
                    )
                )
            )
            if parent is None:
                raise ApiError(status_code=404, code=404, message="Target folder not found")

        folder = Folder(
            owner_id=current_user.user_id,
            parent_folder_id=parent_id,
            folder_name=payload.folder_name,
            status=FolderStatus.ACTIVE,
            folder_type=FolderType.NORMAL,
        )
        self.db.add(folder)
        try:
            await self.db.flush()
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            msg = str(getattr(exc, "orig", exc))
            if "uk_folder_child_name_active" in msg or "uk_folder_root_name_active" in msg:
                raise ApiError(status_code=409, code=409, message="Folder name already exists") from exc
            raise ApiError(status_code=500, code=500, message="Failed to create folder") from exc

        return FolderItem(
            id=str(folder.folder_id),
            name=folder.folder_name,
            size=int(folder.cached_size or 0),
            owner_name=current_user.username,
            updated_at=folder.updated_at,
            created_at=folder.created_at,
            parent_folder_id=str(folder.parent_folder_id) if folder.parent_folder_id is not None else None,
            permission="owner",
        )

    async def get_folder_path(self, *, current_user_id: int, folder_id: int) -> FolderPathResponse:
        # Verify ownership and then walk parents.
        items: list[PathItem] = []
        current = await self.db.scalar(
            select(Folder).where(
                and_(
                    Folder.folder_id == folder_id,
                    Folder.owner_id == current_user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if current is None:
            raise ApiError(status_code=404, code=404, message="Target folder not found")

        # Walk up until root (parent_folder_id is None)
        while current is not None:
            items.append(PathItem(folder_id=str(current.folder_id), name=current.folder_name))
            if current.parent_folder_id is None:
                break
            current = await self.db.scalar(
                select(Folder).where(
                    and_(
                        Folder.folder_id == current.parent_folder_id,
                        Folder.owner_id == current_user_id,
                        Folder.status == FolderStatus.ACTIVE,
                    )
                )
            )

        items.reverse()
        full_path = "/" + "/".join(item.name for item in items)
        return FolderPathResponse(full_path=full_path, path_items=items)

    async def list_folder_contents(
        self,
        *,
        current_user: User,
        folder_id: int,
        query: FolderContentsQuery,
    ) -> PaginatedData[ContentItem]:
        # Folders
        folder_stmt = select(Folder).where(
            and_(
                Folder.owner_id == current_user.user_id,
                Folder.parent_folder_id == folder_id,
                Folder.status == FolderStatus.ACTIVE,
            )
        )
        # Files
        file_stmt = select(File).where(
            and_(
                File.owner_id == current_user.user_id,
                File.folder_id == folder_id,
                File.status == FileStatus.ACTIVE,
            )
        )

        if query.search:
            s = query.search.strip().lower()
            folder_stmt = folder_stmt.where(func.lower(Folder.folder_name).contains(s))
            file_stmt = file_stmt.where(
                or_(
                    func.lower(File.file_name).contains(s),
                    func.lower(func.coalesce(File.mime_type, "")).contains(s),
                )
            )

        folders = list(await self.db.scalars(folder_stmt.order_by(Folder.updated_at.desc())))
        files = list(await self.db.scalars(file_stmt.order_by(File.updated_at.desc())))

        # Merge and paginate in-memory (good enough for course/demo scale)
        items: list[ContentItem] = []
        for f in folders:
            items.append(
                FolderItem(
                    id=str(f.folder_id),
                    name=f.folder_name,
                    size=int(f.cached_size or 0),
                    owner_name=current_user.username,
                    updated_at=f.updated_at,
                    created_at=f.created_at,
                    folder_id=str(f.folder_id),
                    parent_folder_id=str(f.parent_folder_id) if f.parent_folder_id is not None else None,
                    permission="owner",
                )
            )
        for fi in files:
            items.append(
                FileItem(
                    id=str(fi.file_id),
                    name=fi.file_name,
                    size=int(fi.file_size),
                    mime_type=fi.mime_type or "application/octet-stream",
                    owner_name=current_user.username,
                    updated_at=fi.updated_at,
                    created_at=fi.created_at,
                    folder_id=str(fi.folder_id),
                    permission="owner",
                )
            )

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

