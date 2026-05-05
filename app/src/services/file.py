from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..models.enums import FavoriteItemType, FileStatus, FolderStatus, FolderType, ShareStatus
from ..models.tables_access_share import FavoriteItem, Share
from ..models.tables_identity import User
from ..models.tables_storage import File, Folder
from ..schemas.common import PaginatedData, PaginationMeta
from ..schemas.file import (
    BatchFilesRequest,
    BatchFilesResponse,
    BatchMoveItemResult,
    ContentItem,
    FileDetails,
    FileItem,
    GetFilesQuery,
    MoveFileRequest,
    MoveFileResponse,
)

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

    async def move_file(self, *, user_id: int, file_id: str, payload: MoveFileRequest) -> MoveFileResponse:
        moved = await self._move_file_record(
            user_id=user_id,
            file_id=file_id,
            target_folder_id=payload.target_folder_id,
            share_handling=payload.share_handling,
        )
        await self.db.commit()
        return moved

    async def batch_files(self, *, user_id: int, payload: BatchFilesRequest) -> BatchFilesResponse:
        if payload.action != "move":
            raise ApiError(status_code=400, code=400, message="Only move action is currently supported")

        if not payload.target_folder_id:
            raise ApiError(status_code=400, code=400, message="targetFolderId is required for move action")

        file_ids = list(dict.fromkeys(payload.file_ids))
        folder_ids = list(dict.fromkeys(payload.folder_ids))

        if not file_ids and not folder_ids:
            raise ApiError(status_code=400, code=400, message="At least one fileId or folderId is required")

        results: list[BatchMoveItemResult] = []
        succeeded = 0

        for current_file_id in file_ids:
            try:
                moved = await self._move_file_record(
                    user_id=user_id,
                    file_id=current_file_id,
                    target_folder_id=payload.target_folder_id,
                    share_handling=payload.share_handling,
                )
                succeeded += 1
                results.append(
                    BatchMoveItemResult(
                        item_type="file",
                        item_id=moved.file_id,
                        success=True,
                        final_name=moved.final_name,
                        moved_at=moved.moved_at,
                        share_handling=moved.share_handling,
                        revoked_share_count=moved.revoked_share_count,
                    )
                )
            except ApiError as exc:
                results.append(
                    BatchMoveItemResult(
                        item_type="file",
                        item_id=current_file_id,
                        success=False,
                        message=exc.message,
                        share_handling=payload.share_handling,
                    )
                )

        for current_folder_id in folder_ids:
            try:
                moved = await self._move_folder_record(
                    user_id=user_id,
                    folder_id=current_folder_id,
                    target_parent_id=payload.target_folder_id,
                    share_handling=payload.share_handling,
                )
                succeeded += 1
                results.append(
                    BatchMoveItemResult(
                        item_type="folder",
                        item_id=moved["folder_id"],
                        success=True,
                        final_name=moved["final_name"],
                        moved_at=moved["moved_at"],
                        share_handling=moved["share_handling"],
                        revoked_share_count=moved["revoked_share_count"],
                    )
                )
            except ApiError as exc:
                results.append(
                    BatchMoveItemResult(
                        item_type="folder",
                        item_id=current_folder_id,
                        success=False,
                        message=exc.message,
                        share_handling=payload.share_handling,
                    )
                )

        await self.db.commit()
        processed = len(file_ids) + len(folder_ids)
        return BatchFilesResponse(
            processed=processed,
            action=payload.action,
            succeeded=succeeded,
            failed=processed - succeeded,
            results=results,
        )

    async def _move_file_record(
        self,
        *,
        user_id: int,
        file_id: str,
        target_folder_id: str,
        share_handling: str,
    ) -> MoveFileResponse:
        file_row = await self._get_active_file(user_id=user_id, file_id=file_id)
        target_folder_num = await self._resolve_folder_id(user_id, target_folder_id)
        moved_at = datetime.now(UTC)

        final_name = await self._next_available_file_name(
            user_id=user_id,
            folder_id=target_folder_num,
            original_name=file_row.file_name,
            exclude_file_id=file_row.file_id,
        )
        file_row.folder_id = target_folder_num
        file_row.file_name = final_name
        file_row.updated_at = moved_at

        revoked_share_count = 0
        if share_handling == "revoke":
            revoked_share_count = await self._revoke_active_shares(
                user_id=user_id,
                file_ids=[int(file_row.file_id)],
                folder_ids=[],
            )

        return MoveFileResponse(
            file_id=str(file_row.file_id),
            target_folder_id=str(target_folder_num),
            final_name=final_name,
            share_handling=share_handling,
            revoked_share_count=revoked_share_count,
            moved_at=moved_at,
        )

    async def _move_folder_record(
        self,
        *,
        user_id: int,
        folder_id: str,
        target_parent_id: str,
        share_handling: str,
    ) -> dict[str, str | int | datetime]:
        folder_row = await self._get_active_folder(user_id=user_id, folder_id=folder_id)
        if folder_row.folder_type == FolderType.ROOT:
            raise ApiError(status_code=400, code=400, message="Root folder cannot be moved")

        target_parent_num = await self._resolve_folder_id(user_id, target_parent_id)
        if target_parent_num == int(folder_row.folder_id):
            raise ApiError(status_code=409, code=409, message="Cannot move a folder into itself")

        if await self._is_descendant_folder(user_id=user_id, folder_id=target_parent_num, ancestor_id=int(folder_row.folder_id)):
            raise ApiError(status_code=409, code=409, message="Cannot move a folder into its descendant")

        moved_at = datetime.now(UTC)
        final_name = await self._next_available_folder_name(
            user_id=user_id,
            parent_folder_id=target_parent_num,
            original_name=folder_row.folder_name,
            exclude_folder_id=folder_row.folder_id,
        )
        folder_row.parent_folder_id = target_parent_num
        folder_row.folder_name = final_name
        folder_row.updated_at = moved_at

        revoked_share_count = 0
        if share_handling == "revoke":
            folder_ids, file_ids = await self._collect_folder_subtree(user_id=user_id, root_folder_id=int(folder_row.folder_id))
            revoked_share_count = await self._revoke_active_shares(
                user_id=user_id,
                file_ids=file_ids,
                folder_ids=folder_ids,
            )

        return {
            "folder_id": str(folder_row.folder_id),
            "target_parent_id": str(target_parent_num),
            "final_name": final_name,
            "share_handling": share_handling,
            "revoked_share_count": revoked_share_count,
            "moved_at": moved_at,
        }

    async def _get_active_file(self, *, user_id: int, file_id: str) -> File:
        fid = self._parse_id(file_id, "fileId")
        file_row = await self.db.scalar(
            select(File).where(
                and_(
                    File.file_id == fid,
                    File.owner_id == user_id,
                    File.status == FileStatus.ACTIVE,
                    File.is_latest.is_(True),
                )
            )
        )
        if file_row is None:
            raise ApiError(status_code=404, code=404, message="File not found")
        return file_row

    async def _get_active_folder(self, *, user_id: int, folder_id: str) -> Folder:
        fid = self._parse_id(folder_id, "folderId")
        folder_row = await self.db.scalar(
            select(Folder).where(
                and_(
                    Folder.folder_id == fid,
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if folder_row is None:
            raise ApiError(status_code=404, code=404, message="Folder not found")
        return folder_row

    async def _revoke_active_shares(
        self,
        *,
        user_id: int,
        file_ids: list[int],
        folder_ids: list[int],
    ) -> int:
        if not file_ids and not folder_ids:
            return 0

        targets = []
        if file_ids:
            targets.append(Share.file_id.in_(file_ids))
        if folder_ids:
            targets.append(Share.folder_id.in_(folder_ids))

        stmt = select(Share.share_id).where(
            and_(
                Share.user_id == user_id,
                Share.status == ShareStatus.ACTIVE,
                or_(*targets),
            )
        )
        share_ids = list(await self.db.scalars(stmt))
        if not share_ids:
            return 0

        await self.db.execute(
            update(Share)
            .where(Share.share_id.in_(share_ids))
            .values(status=ShareStatus.DELETED)
        )
        return len(share_ids)

    async def _collect_folder_subtree(self, *, user_id: int, root_folder_id: int) -> tuple[list[int], list[int]]:
        descendants = (
            select(Folder.folder_id)
            .where(
                and_(
                    Folder.folder_id == root_folder_id,
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
            .cte(name="move_descendants", recursive=True)
        )
        descendants = descendants.union_all(
            select(Folder.folder_id).where(
                and_(
                    Folder.parent_folder_id == descendants.c.folder_id,
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )

        folder_ids = list(await self.db.scalars(select(descendants.c.folder_id)))
        if not folder_ids:
            return [], []

        file_ids = list(
            await self.db.scalars(
                select(File.file_id).where(
                    and_(
                        File.owner_id == user_id,
                        File.status == FileStatus.ACTIVE,
                        File.is_latest.is_(True),
                        File.folder_id.in_(folder_ids),
                    )
                )
            )
        )
        return folder_ids, file_ids

    async def _is_descendant_folder(self, *, user_id: int, folder_id: int, ancestor_id: int) -> bool:
        cursor = folder_id
        while True:
            if cursor == ancestor_id:
                return True
            parent = await self.db.scalar(
                select(Folder.parent_folder_id).where(
                    and_(
                        Folder.folder_id == cursor,
                        Folder.owner_id == user_id,
                        Folder.status == FolderStatus.ACTIVE,
                    )
                )
            )
            if parent is None:
                return False
            cursor = int(parent)

    async def _next_available_file_name(
        self,
        *,
        user_id: int,
        folder_id: int,
        original_name: str,
        exclude_file_id: int | None = None,
    ) -> str:
        candidate = original_name
        if await self._find_conflict_file(
            user_id=user_id,
            folder_id=folder_id,
            file_name=candidate,
            exclude_file_id=exclude_file_id,
        ) is None:
            return candidate

        stem = Path(original_name).stem or "file"
        suffix = Path(original_name).suffix
        index = 1
        while True:
            candidate = f"{stem} ({index}){suffix}"
            conflict = await self._find_conflict_file(
                user_id=user_id,
                folder_id=folder_id,
                file_name=candidate,
                exclude_file_id=exclude_file_id,
            )
            if conflict is None:
                return candidate
            index += 1

    async def _next_available_folder_name(
        self,
        *,
        user_id: int,
        parent_folder_id: int,
        original_name: str,
        exclude_folder_id: int | None = None,
    ) -> str:
        candidate = original_name
        if await self._find_conflict_folder(
            user_id=user_id,
            parent_folder_id=parent_folder_id,
            folder_name=candidate,
            exclude_folder_id=exclude_folder_id,
        ) is None:
            return candidate

        stem = original_name.strip() or "Folder"
        index = 1
        while True:
            candidate = f"{stem} ({index})"
            conflict = await self._find_conflict_folder(
                user_id=user_id,
                parent_folder_id=parent_folder_id,
                folder_name=candidate,
                exclude_folder_id=exclude_folder_id,
            )
            if conflict is None:
                return candidate
            index += 1

    async def _find_conflict_file(
        self,
        *,
        user_id: int,
        folder_id: int,
        file_name: str,
        exclude_file_id: int | None = None,
    ) -> File | None:
        clauses = [
            File.owner_id == user_id,
            File.folder_id == folder_id,
            File.file_name == file_name,
            File.status == FileStatus.ACTIVE,
            File.is_latest.is_(True),
        ]
        if exclude_file_id is not None:
            clauses.append(File.file_id != exclude_file_id)

        return await self.db.scalar(select(File).where(and_(*clauses)).limit(1))

    async def _find_conflict_folder(
        self,
        *,
        user_id: int,
        parent_folder_id: int,
        folder_name: str,
        exclude_folder_id: int | None = None,
    ) -> Folder | None:
        clauses = [
            Folder.owner_id == user_id,
            Folder.parent_folder_id == parent_folder_id,
            Folder.folder_name == folder_name,
            Folder.status == FolderStatus.ACTIVE,
        ]
        if exclude_folder_id is not None:
            clauses.append(Folder.folder_id != exclude_folder_id)

        return await self.db.scalar(select(Folder).where(and_(*clauses)).limit(1))

    @staticmethod
    def _parse_id(raw: str, field_name: str) -> int:
        try:
            value = int(raw)
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message=f"Invalid {field_name}") from exc
        if value <= 0:
            raise ApiError(status_code=400, code=400, message=f"Invalid {field_name}")
        return value

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
            return int(folder.folder_id)

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
        return int(fid)

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
