from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..core.mime import resolve_file_mime_type
from ..db.transaction import (
    apply_local_lock_timeout,
    is_retryable_database_error,
    is_unique_violation_error,
    run_with_transaction_retry,
    to_retryable_concurrency_error,
)
from ..models.enums import FavoriteItemType, FileStatus, FolderStatus, FolderType
from ..models.tables_access_share import FavoriteItem
from ..models.tables_identity import User
from ..models.tables_storage import File, FileMediaMetadata, Folder
from ..schemas.common import PaginatedData, PaginationMeta
from ..schemas.file import (
    ContentItem,
    CreateFolderRequest,
    DeleteFolderResponse,
    FileItem,
    FolderItem,
    FolderPathResponse,
    FolderSizeResponse,
    GetFolderContentsQuery,
    MediaOptimization,
    MoveFolderRequest,
    MoveFolderResponse,
    PathItem,
    RenameFolderRequest,
)
from .file import FileService

_SORT_COLUMNS_FILE = {
    "name": File.file_name,
    "size": File.file_size,
    "createdAt": File.created_at,
    "updatedAt": File.updated_at,
}
_SORT_COLUMNS_FOLDER = {
    "name": Folder.folder_name,
    "size": Folder.cached_size,
    "createdAt": Folder.created_at,
    "updatedAt": Folder.updated_at,
}


class FolderService:
    def __init__(self, *, db: AsyncSession, starred_items_limit: int = 20) -> None:
        self.db = db
        self.starred_items_limit = starred_items_limit

    async def get_root_contents(
        self, *, user_id: int, query: GetFolderContentsQuery,
    ) -> PaginatedData[ContentItem]:
        root = await self._get_root_folder(user_id)
        query.folder_id = str(root.folder_id)
        return await self.get_folder_contents(user_id=user_id, query=query)

    async def get_root_folder_id(self, *, user_id: int) -> int:
        root = await self._get_root_folder(user_id)
        return int(root.folder_id)

    async def get_folder_contents(
        self, *, user_id: int, query: GetFolderContentsQuery,
    ) -> PaginatedData[ContentItem]:
        folder_id = self._parse_id(query.folder_id, "folderId")
        await self._ensure_folder_access(user_id, folder_id)

        # sub-folders
        folder_q = (
            select(Folder, User.username)
            .join(User, User.user_id == Folder.owner_id)
            .where(
                and_(
                    Folder.parent_folder_id == folder_id,
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if query.search:
            folder_q = folder_q.where(func.lower(Folder.folder_name).contains(query.search.lower()))

        fcol = _SORT_COLUMNS_FOLDER.get(query.sort or "name", Folder.folder_name)
        folder_q = folder_q.order_by(fcol.desc() if query.order == "desc" else fcol.asc())
        folder_rows = (await self.db.execute(folder_q)).all()

        # files
        file_q = (
            select(File, User.username)
            .join(User, User.user_id == File.owner_id)
            .where(
                and_(
                    File.folder_id == folder_id,
                    File.owner_id == user_id,
                    File.status == FileStatus.ACTIVE,
                    File.is_latest.is_(True),
                )
            )
        )
        if query.search:
            file_q = file_q.where(func.lower(File.file_name).contains(query.search.lower()))

        col = _SORT_COLUMNS_FILE.get(query.sort or "name", File.file_name)
        file_q = file_q.order_by(col.desc() if query.order == "desc" else col.asc())
        file_rows = (await self.db.execute(file_q)).all()

        # starred lookup
        folder_ids = [r[0].folder_id for r in folder_rows]
        file_ids = [r[0].file_id for r in file_rows]
        starred_folders = await self._starred_folder_ids(user_id, folder_ids)
        starred_files = await self._starred_file_ids(user_id, file_ids)
        media_optimization_map = await self._load_media_optimization_map([f for f, _ in file_rows])

        # merge: folders first, then files
        all_items: list[ContentItem] = []
        for folder, uname in folder_rows:
            all_items.append(self._to_folder_item(folder, uname, folder.folder_id in starred_folders))
        for f, uname in file_rows:
            all_items.append(
                self._to_file_item(
                    f,
                    uname,
                    f.file_id in starred_files,
                    media_optimization=media_optimization_map.get(int(f.file_id)),
                )
            )

        total = len(all_items)
        per_page = query.per_page
        offset = (query.page - 1) * per_page
        page_items = all_items[offset : offset + per_page]

        return self._paginate(page_items, total, query.page, per_page)

    async def list_folders(self, *, user_id: int, parent_id: str | None, page: int, per_page: int) -> PaginatedData[FolderItem]:
        base = (
            select(Folder, User.username)
            .join(User, User.user_id == Folder.owner_id)
            .where(and_(Folder.owner_id == user_id, Folder.status == FolderStatus.ACTIVE))
        )
        if parent_id:
            pid = self._parse_id(parent_id, "parentId")
            base = base.where(Folder.parent_folder_id == pid)

        base = base.order_by(Folder.folder_name.asc())
        total = await self.db.scalar(select(func.count()).select_from(base.subquery()))
        total = total or 0

        offset = (page - 1) * per_page
        rows = (await self.db.execute(base.offset(offset).limit(per_page))).all()

        starred = await self._starred_folder_ids(user_id, [r[0].folder_id for r in rows])
        items = [self._to_folder_item(folder, uname, folder.folder_id in starred) for folder, uname in rows]
        return self._paginate(items, total, page, per_page)

    async def create_folder(self, *, user_id: int, payload: CreateFolderRequest) -> FolderItem:
        folder_name = payload.folder_name.strip()
        if not folder_name:
            raise ApiError(status_code=400, code=400, message="folderName cannot be empty")

        parent_folder_id = await self._resolve_parent_folder_id(user_id=user_id, parent_id=payload.parent_folder_id)
        owner = await self.db.get(User, user_id)
        if owner is None:
            raise ApiError(status_code=404, code=404, message="User not found")

        final_name = await self._next_available_folder_name(
            user_id=user_id,
            parent_folder_id=parent_folder_id,
            original_name=folder_name,
        )
        now = datetime.now(UTC)
        folder = Folder(
            owner_id=user_id,
            parent_folder_id=parent_folder_id,
            folder_name=final_name,
            cached_size=0,
            status=FolderStatus.ACTIVE,
            folder_type=FolderType.NORMAL,
            created_at=now,
            updated_at=now,
        )
        self.db.add(folder)
        await self.db.commit()
        await self.db.refresh(folder)
        return self._to_folder_item(folder, owner.username, False)

    async def rename_folder(
        self,
        *,
        user_id: int,
        folder_id: str,
        payload: RenameFolderRequest,
    ) -> FolderItem:
        try:
            fid = int(folder_id)
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message="Invalid folderId") from exc

        folder = await self.db.scalar(
            select(Folder)
            .where(
                and_(
                    Folder.folder_id == fid,
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
            .with_for_update()
        )
        if folder is None:
            raise ApiError(status_code=404, code=404, message="Folder not found")
        if folder.folder_type == FolderType.ROOT:
            raise ApiError(status_code=400, code=400, message="Root folder cannot be renamed")

        requested_name = payload.folder_name.strip()
        if not requested_name:
            raise ApiError(status_code=400, code=400, message="folderName cannot be empty")

        parent_folder_id = int(folder.parent_folder_id or 0)
        final_name = await self._next_available_folder_name(
            user_id=user_id,
            parent_folder_id=parent_folder_id,
            original_name=requested_name,
            exclude_folder_id=fid,
        )
        folder.folder_name = final_name
        folder.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(folder)

        owner = await self.db.get(User, user_id)
        owner_name = owner.username if owner else "owner"
        is_starred = bool(await self._starred_folder_ids(user_id, [fid]))
        return self._to_folder_item(folder, owner_name, is_starred)

    async def toggle_folder_star(
        self,
        *,
        user_id: int,
        folder_id: str,
        is_starred: bool,
    ) -> FolderItem:
        fid = self._parse_id(folder_id, "folderId")
        folder = await self.db.scalar(
            select(Folder)
            .where(
                and_(
                    Folder.folder_id == fid,
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
            .with_for_update()
        )
        if folder is None:
            raise ApiError(status_code=404, code=404, message="Folder not found")

        favorite = await self._get_folder_favorite(user_id=user_id, folder_id=fid)

        if is_starred and favorite is None:
            await self._lock_user_for_star_update(user_id=user_id)
            favorite = await self._get_folder_favorite(user_id=user_id, folder_id=fid)
            if favorite is None:
                starred_count = await self._count_starred_items(user_id=user_id)
                if starred_count >= self.starred_items_limit:
                    raise ApiError(
                        status_code=400,
                        code=400,
                        message=f"已达收藏上限 {self.starred_items_limit}",
                    )
                self.db.add(
                    FavoriteItem(
                        user_id=user_id,
                        item_type=FavoriteItemType.FOLDER,
                        file_id=None,
                        folder_id=fid,
                    )
                )
        elif not is_starred and favorite is not None:
            await self.db.delete(favorite)

        await self.db.commit()
        owner = await self.db.get(User, user_id)
        owner_name = owner.username if owner else "owner"
        return self._to_folder_item(folder, owner_name, is_starred)

    async def get_folder_path(self, *, user_id: int, folder_id: int) -> FolderPathResponse:
        path_items: list[PathItem] = []
        current_id: int | None = folder_id

        while current_id is not None:
            folder = await self.db.scalar(
                select(Folder).where(
                    and_(Folder.folder_id == current_id, Folder.owner_id == user_id, Folder.status == FolderStatus.ACTIVE)
                )
            )
            if folder is None:
                raise ApiError(status_code=404, code=404, message="Folder not found")
            path_item_id = "root" if folder.parent_folder_id is None else str(folder.folder_id)
            path_items.append(PathItem(folder_id=path_item_id, name=folder.folder_name))
            current_id = folder.parent_folder_id

        path_items.reverse()
        full_path = "/".join(item.name for item in path_items)
        return FolderPathResponse(full_path=full_path, path_items=path_items)

    async def get_folder_size(self, *, user_id: int, folder_id: int) -> FolderSizeResponse:
        await self._ensure_folder_access(user_id, folder_id)

        # Recursive CTE to collect all descendant folder IDs
        cte = (
            select(Folder.folder_id)
            .where(and_(Folder.folder_id == folder_id, Folder.status == FolderStatus.ACTIVE))
            .cte(name="descendants", recursive=True)
        )
        cte = cte.union_all(
            select(Folder.folder_id).where(
                and_(Folder.parent_folder_id == cte.c.folder_id, Folder.status == FolderStatus.ACTIVE)
            )
        )

        all_folder_ids = select(cte.c.folder_id)

        total_size = await self.db.scalar(
            select(func.coalesce(func.sum(File.file_size), 0)).where(
                and_(File.folder_id.in_(all_folder_ids), File.status == FileStatus.ACTIVE, File.is_latest.is_(True))
            )
        )
        file_count = await self.db.scalar(
            select(func.count()).where(
                and_(File.folder_id.in_(all_folder_ids), File.status == FileStatus.ACTIVE, File.is_latest.is_(True))
            )
        )
        folder_count = await self.db.scalar(select(func.count()).select_from(all_folder_ids.subquery()))
        # exclude the folder itself from count
        folder_count = max(0, (folder_count or 0) - 1)

        return FolderSizeResponse(
            total_size=total_size or 0,
            file_count=file_count or 0,
            folder_count=folder_count,
        )

    async def move_folder(
        self, *, user_id: int, folder_id: str, payload: MoveFolderRequest,
    ) -> MoveFolderResponse:
        async def _operation() -> MoveFolderResponse:
            await apply_local_lock_timeout(self.db)
            mover = FileService(db=self.db)
            moved = await mover._move_folder_record(
                user_id=user_id,
                folder_id=folder_id,
                target_parent_id=payload.target_parent_id,
                share_handling=payload.share_handling,
            )
            await self.db.commit()
            return MoveFolderResponse(
                folder_id=str(moved["folder_id"]),
                target_parent_id=str(moved["target_parent_id"]),
                final_name=str(moved["final_name"]),
                share_handling=str(moved["share_handling"]),
                revoked_share_count=int(moved["revoked_share_count"]),
                moved_at=moved["moved_at"],
            )

        try:
            return await run_with_transaction_retry(
                self.db,
                _operation,
                retry_on_unique_violation=True,
            )
        except Exception as exc:  # noqa: BLE001
            if is_retryable_database_error(exc) or is_unique_violation_error(exc):
                raise to_retryable_concurrency_error(exc) from exc
            raise

    async def delete_folder(self, *, user_id: int, folder_id: str) -> DeleteFolderResponse:
        deleter = FileService(db=self.db)
        return await deleter.delete_folder(user_id=user_id, folder_id=folder_id)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    async def _resolve_parent_folder_id(self, *, user_id: int, parent_id: str | None) -> int:
        if parent_id is None or parent_id == "root":
            root = await self._get_root_folder(user_id)
            return int(root.folder_id)

        try:
            parent_folder_id = int(parent_id)
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message="Invalid parentFolderId") from exc

        await self._ensure_folder_access(user_id, parent_folder_id)
        return parent_folder_id

    async def _next_available_folder_name(
        self,
        *,
        user_id: int,
        parent_folder_id: int,
        original_name: str,
        exclude_folder_id: int | None = None,
    ) -> str:
        normalized = original_name.strip() or "Folder"
        candidate = normalized

        def _exists_query(name: str):
            clauses = [
                Folder.owner_id == user_id,
                Folder.parent_folder_id == parent_folder_id,
                Folder.folder_name == name,
                Folder.status == FolderStatus.ACTIVE,
            ]
            if exclude_folder_id is not None:
                clauses.append(Folder.folder_id != exclude_folder_id)
            return select(Folder.folder_id).where(and_(*clauses)).limit(1)

        exists = await self.db.scalar(_exists_query(candidate))
        if exists is None:
            return candidate

        index = 1
        while True:
            candidate = f"{normalized} ({index})"
            exists = await self.db.scalar(_exists_query(candidate))
            if exists is None:
                return candidate
            index += 1

    async def _get_root_folder(self, user_id: int) -> Folder:
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
        return folder

    async def _ensure_folder_access(self, user_id: int, folder_id: int) -> None:
        exists = await self.db.scalar(
            select(Folder.folder_id).where(
                and_(Folder.folder_id == folder_id, Folder.owner_id == user_id, Folder.status == FolderStatus.ACTIVE)
            )
        )
        if exists is None:
            raise ApiError(status_code=404, code=404, message="Folder not found")

    async def _get_folder_favorite(self, *, user_id: int, folder_id: int) -> FavoriteItem | None:
        return await self.db.scalar(
            select(FavoriteItem).where(
                and_(
                    FavoriteItem.user_id == user_id,
                    FavoriteItem.item_type == FavoriteItemType.FOLDER,
                    FavoriteItem.folder_id == folder_id,
                )
            )
        )

    async def _lock_user_for_star_update(self, *, user_id: int) -> None:
        locked_user = await self.db.scalar(
            select(User.user_id).where(User.user_id == user_id).with_for_update()
        )
        if locked_user is None:
            raise ApiError(status_code=404, code=404, message="User not found")

    async def _count_starred_items(self, *, user_id: int) -> int:
        count = await self.db.scalar(
            select(func.count(FavoriteItem.favorite_id)).where(FavoriteItem.user_id == user_id)
        )
        return int(count or 0)

    async def _starred_file_ids(self, user_id: int, file_ids: list[int]) -> set[int]:
        if not file_ids:
            return set()
        return set(
            await self.db.scalars(
                select(FavoriteItem.file_id).where(
                    and_(
                        FavoriteItem.user_id == user_id,
                        FavoriteItem.item_type == FavoriteItemType.FILE,
                        FavoriteItem.file_id.in_(file_ids),
                    )
                )
            )
        )

    async def _starred_folder_ids(self, user_id: int, folder_ids: list[int]) -> set[int]:
        if not folder_ids:
            return set()
        return set(
            await self.db.scalars(
                select(FavoriteItem.folder_id).where(
                    and_(
                        FavoriteItem.user_id == user_id,
                        FavoriteItem.item_type == FavoriteItemType.FOLDER,
                        FavoriteItem.folder_id.in_(folder_ids),
                    )
                )
            )
        )

    @staticmethod
    def _parse_id(value: str, name: str) -> int:
        try:
            return int(value)
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message=f"Invalid {name}") from exc

    async def _load_media_optimization_map(self, files: list[File]) -> dict[int, MediaOptimization]:
        if not files:
            return {}
        source_object_ids = [int(row.storage_object_id) for row in files if row.storage_object_id is not None]
        if not source_object_ids:
            return {}

        metadata_rows = list(
            await self.db.scalars(
                select(FileMediaMetadata).where(FileMediaMetadata.source_object_id.in_(source_object_ids))
            )
        )
        by_object_id = {
            int(row.source_object_id): row for row in metadata_rows if isinstance(row, FileMediaMetadata)
        }
        result: dict[int, MediaOptimization] = {}
        for row in files:
            media = self._parse_media_optimization(by_object_id.get(int(row.storage_object_id)))
            if media is not None:
                result[int(row.file_id)] = media
        return result

    @staticmethod
    def _parse_media_optimization(metadata_row: FileMediaMetadata | None) -> MediaOptimization | None:
        if metadata_row is None:
            return None
        transcode = (metadata_row.extra_metadata or {}).get("transcode")
        if not isinstance(transcode, dict):
            return None
        status = str(transcode.get("status") or "").strip().lower()
        media_type = str(transcode.get("mediaType") or "").strip().lower()
        if status not in {"queued", "running", "ready", "failed"}:
            return None
        if media_type not in {"audio", "video"}:
            return None
        updated_at_raw = transcode.get("updatedAt")
        if isinstance(updated_at_raw, datetime):
            updated_at = updated_at_raw
        else:
            text = str(updated_at_raw or "").strip()
            try:
                updated_at = datetime.fromisoformat(text.replace("Z", "+00:00")) if text else metadata_row.extracted_at
            except ValueError:
                updated_at = metadata_row.extracted_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        optimized_mime_type = transcode.get("optimizedMimeType")
        return MediaOptimization(
            status=status,  # type: ignore[arg-type]
            media_type=media_type,  # type: ignore[arg-type]
            optimized_mime_type=str(optimized_mime_type) if optimized_mime_type else None,
            updated_at=updated_at,
        )

    @staticmethod
    def _to_file_item(
        f: File,
        owner_name: str,
        is_starred: bool,
        *,
        media_optimization: MediaOptimization | None = None,
    ) -> FileItem:
        return FileItem(
            id=str(f.file_id),
            name=f.file_name,
            size=f.file_size,
            mime_type=resolve_file_mime_type(
                mime_type=f.mime_type,
                file_ext=f.file_ext,
                file_name=f.file_name,
            ),
            owner_name=owner_name,
            updated_at=f.updated_at,
            created_at=f.created_at,
            folder_id=str(f.folder_id),
            permission="owner",
            is_starred=is_starred,
            media_optimization=media_optimization,
        )

    @staticmethod
    def _to_folder_item(folder: Folder, owner_name: str, is_starred: bool) -> FolderItem:
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
