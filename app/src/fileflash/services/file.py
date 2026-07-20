from __future__ import annotations

import os
import tempfile
import zipfile
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..core.http_headers import build_content_disposition
from ..core.mime import DEFAULT_MIME_TYPE, resolve_file_mime_type
from ..db.transaction import (
    apply_local_lock_timeout,
    is_retryable_database_error,
    is_unique_violation_error,
    run_with_transaction_retry,
    to_retryable_concurrency_error,
)
from ..models.enums import (
    FavoriteItemType,
    FileStatus,
    FolderStatus,
    FolderType,
    ShareStatus,
    UploadStatus,
)
from ..models.tables_access_share import FavoriteItem, Share
from ..models.tables_identity import User
from ..models.tables_storage import File, FileMediaMetadata, Folder, StorageObject
from ..s3.minio_client import MinioObjectStorageClient
from ..schemas.common import PaginatedData, PaginationMeta
from ..schemas.file import (
    BatchDownloadRequest,
    BatchFilesRequest,
    BatchFilesResponse,
    BatchMoveItemResult,
    ContentItem,
    DeleteFileResponse,
    DeleteFolderResponse,
    FileDetails,
    FileItem,
    GetFilesQuery,
    MediaOptimization,
    MoveFileRequest,
    MoveFileResponse,
    RenameFileRequest,
)
from ..schemas.recycle import (
    ClearRecycleBinResponse,
    GetRecycleBinQuery,
    PermanentDeleteResponse,
    RecycleBinItem,
    RestoreRecycleItemRequest,
    RestoreRecycleItemResponse,
)

_SORT_COLUMNS = {
    "name": File.file_name,
    "size": File.file_size,
    "createdAt": File.created_at,
    "updatedAt": File.updated_at,
}

_RECYCLE_RETENTION_DAYS = 30

TRANSCODE_READY_STATUS = "ready"


@dataclass(slots=True)
class DownloadStreamResult:
    stream: AsyncIterator[bytes]
    filename: str
    content_type: str
    status_code: int
    headers: dict[str, str]


@dataclass(slots=True)
class BatchDownloadPlan:
    files: list[tuple[File, StorageObject, str]]
    estimated_bytes: int


@dataclass(slots=True)
class ResolvedStreamObject:
    storage_object: StorageObject
    content_type_override: str | None = None


class FileService:
    def __init__(
        self,
        *,
        db: AsyncSession,
        storage: MinioObjectStorageClient | None = None,
        starred_items_limit: int = 20,
    ) -> None:
        self.db = db
        self.storage = storage
        self.starred_items_limit = starred_items_limit

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
        media_optimization_map = await self._load_media_optimization_map([r[0] for r in rows])

        items = [
            self._to_file_item(
                f,
                username,
                f.file_id in starred_ids,
                media_optimization=media_optimization_map.get(int(f.file_id)),
            )
            for f, username in rows
        ]
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
        media_optimization = await self._load_file_media_optimization(f)
        return FileDetails(
            id=str(f.file_id),
            name=f.file_name,
            size=f.file_size,
            mime_type=resolve_file_mime_type(
                mime_type=f.mime_type,
                file_ext=f.file_ext,
                file_name=f.file_name,
            ),
            owner_name=username,
            updated_at=f.updated_at,
            created_at=f.created_at,
            folder_id=str(f.folder_id),
            permission="owner",
            is_starred=is_starred,
            media_optimization=media_optimization,
            status=True,
        )

    async def rename_file(
        self,
        *,
        user_id: int,
        file_id: str,
        payload: RenameFileRequest,
    ) -> FileDetails:
        async def _operation() -> int:
            await apply_local_lock_timeout(self.db)
            file_row = await self._get_active_file(user_id=user_id, file_id=file_id, for_update=True)

            requested_name = payload.file_name.strip()
            if not requested_name:
                raise ApiError(status_code=400, code=400, message="fileName cannot be empty")

            file_row.file_name = await self._next_available_file_name(
                user_id=user_id,
                folder_id=int(file_row.folder_id),
                original_name=requested_name,
                exclude_file_id=int(file_row.file_id),
            )
            file_row.updated_at = datetime.now(UTC)
            await self.db.commit()
            return int(file_row.file_id)

        try:
            renamed_file_id = await run_with_transaction_retry(
                self.db,
                _operation,
                retry_on_unique_violation=True,
            )
        except Exception as exc:  # noqa: BLE001
            if is_retryable_database_error(exc) or is_unique_violation_error(exc):
                raise to_retryable_concurrency_error(exc) from exc
            raise

        return await self.get_file(user_id=user_id, file_id=renamed_file_id)

    async def toggle_file_star(
        self,
        *,
        user_id: int,
        file_id: str,
        is_starred: bool,
    ) -> FileDetails:
        file_row = await self._get_active_file(user_id=user_id, file_id=file_id, for_update=True)
        favorite = await self._get_file_favorite(user_id=user_id, file_id=int(file_row.file_id))

        if is_starred and favorite is None:
            await self._lock_user_for_star_update(user_id=user_id)
            favorite = await self._get_file_favorite(user_id=user_id, file_id=int(file_row.file_id))
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
                        item_type=FavoriteItemType.FILE,
                        file_id=int(file_row.file_id),
                        folder_id=None,
                    )
                )
        elif not is_starred and favorite is not None:
            await self.db.delete(favorite)

        await self.db.commit()
        return await self.get_file(user_id=user_id, file_id=int(file_row.file_id))

    async def get_download_stream(
        self,
        *,
        user_id: int,
        file_id: str,
        range_header: str | None,
    ) -> DownloadStreamResult:
        return await self._get_file_stream(
            user_id=user_id,
            file_id=file_id,
            range_header=range_header,
            content_disposition="attachment",
        )

    async def get_preview_stream(
        self,
        *,
        user_id: int,
        file_id: str,
        range_header: str | None,
    ) -> DownloadStreamResult:
        return await self._get_file_stream(
            user_id=user_id,
            file_id=file_id,
            range_header=range_header,
            content_disposition="inline",
        )

    async def _get_file_stream(
        self,
        *,
        user_id: int,
        file_id: str,
        range_header: str | None,
        content_disposition: Literal["attachment", "inline"],
    ) -> DownloadStreamResult:
        if self.storage is None:
            raise ApiError(status_code=503, code=503, message="Object storage is unavailable")

        file_row = await self._get_active_file(user_id=user_id, file_id=file_id)
        resolved_object = await self._resolve_stream_storage_object(
            file_row=file_row,
            prefer_optimized=(content_disposition == "inline"),
        )
        storage_object = resolved_object.storage_object if resolved_object is not None else None
        if storage_object is None or storage_object.upload_status != UploadStatus.ACTIVE:
            raise ApiError(status_code=404, code=404, message="File content not found")

        object_size = int(storage_object.object_size or file_row.file_size or 0)
        if object_size <= 0:
            raise ApiError(status_code=404, code=404, message="File content not found")

        content_type = resolve_file_mime_type(
            mime_type=(
                resolved_object.content_type_override
                if resolved_object is not None and resolved_object.content_type_override
                else file_row.mime_type or storage_object.content_type
            ),
            file_ext=file_row.file_ext,
            file_name=file_row.file_name,
            default=DEFAULT_MIME_TYPE,
        )
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": self._build_content_disposition_header(
                file_row.file_name,
                disposition=content_disposition,
            ),
        }

        byte_range = self._parse_range_header(range_header=range_header, file_size=object_size)
        if byte_range is None:
            headers["Content-Length"] = str(object_size)
            stream = self.storage.iter_object(
                bucket_name=storage_object.bucket_name,
                object_key=storage_object.object_key,
            )
            return DownloadStreamResult(
                stream=stream,
                filename=file_row.file_name,
                content_type=content_type,
                status_code=200,
                headers=headers,
            )

        start, end = byte_range
        headers["Content-Length"] = str(end - start + 1)
        headers["Content-Range"] = f"bytes {start}-{end}/{object_size}"
        stream = self.storage.iter_object_range(
            bucket_name=storage_object.bucket_name,
            object_key=storage_object.object_key,
            start=start,
            end=end,
        )
        return DownloadStreamResult(
            stream=stream,
            filename=file_row.file_name,
            content_type=content_type,
            status_code=206,
            headers=headers,
        )

    async def create_batch_download_archive(
        self,
        *,
        user_id: int,
        payload: BatchDownloadRequest,
    ) -> tuple[str, str]:
        plan = await self.create_batch_download_plan(user_id=user_id, payload=payload)
        return await self.create_batch_download_archive_from_plan(plan=plan)

    async def create_batch_download_plan(
        self,
        *,
        user_id: int,
        payload: BatchDownloadRequest,
    ) -> BatchDownloadPlan:
        if self.storage is None:
            raise ApiError(status_code=503, code=503, message="Object storage is unavailable")

        file_ids = self._dedupe_ids(payload.file_ids, "fileId")
        folder_ids = self._dedupe_ids(payload.folder_ids, "folderId")
        if not file_ids and not folder_ids:
            raise ApiError(status_code=400, code=400, message="At least one fileId or folderId is required")

        file_paths: dict[int, str] = {}

        if file_ids:
            direct_rows = list(
                await self.db.scalars(
                    select(File).where(
                        and_(
                            File.file_id.in_(file_ids),
                            File.owner_id == user_id,
                            File.status == FileStatus.ACTIVE,
                            File.is_latest.is_(True),
                        )
                    )
                )
            )
            for row in direct_rows:
                file_paths[int(row.file_id)] = row.file_name

        for folder_id in folder_ids:
            folder_path_map = await self._build_active_subtree_paths(user_id=user_id, root_folder_id=folder_id)
            if not folder_path_map:
                continue
            subtree_file_rows = list(
                await self.db.scalars(
                    select(File).where(
                        and_(
                            File.owner_id == user_id,
                            File.status == FileStatus.ACTIVE,
                            File.is_latest.is_(True),
                            File.folder_id.in_(list(folder_path_map.keys())),
                        )
                    )
                )
            )
            for row in subtree_file_rows:
                folder_path = folder_path_map.get(int(row.folder_id), "")
                zip_path = f"{folder_path}/{row.file_name}" if folder_path else row.file_name
                file_paths.setdefault(int(row.file_id), zip_path)

        if not file_paths:
            raise ApiError(status_code=404, code=404, message="No downloadable files found")

        files_with_storage = (
            await self.db.execute(
                select(File, StorageObject)
                .join(StorageObject, StorageObject.object_id == File.storage_object_id)
                .where(
                    and_(
                        File.file_id.in_(list(file_paths.keys())),
                        File.owner_id == user_id,
                        File.status == FileStatus.ACTIVE,
                        File.is_latest.is_(True),
                        StorageObject.upload_status == UploadStatus.ACTIVE,
                    )
                )
            )
        ).all()

        if not files_with_storage:
            raise ApiError(status_code=404, code=404, message="No downloadable files found")

        files = [
            (
                file_row,
                storage_object,
                self._safe_zip_path(file_paths.get(int(file_row.file_id), file_row.file_name)),
            )
            for file_row, storage_object in files_with_storage
        ]
        estimated_bytes = sum(
            int(storage_object.object_size or file_row.file_size or 0)
            for file_row, storage_object, _zip_path in files
        )
        return BatchDownloadPlan(files=files, estimated_bytes=max(0, estimated_bytes))

    async def create_batch_download_archive_from_plan(
        self,
        *,
        plan: BatchDownloadPlan,
    ) -> tuple[str, str]:
        if self.storage is None:
            raise ApiError(status_code=503, code=503, message="Object storage is unavailable")

        if not plan.files:
            raise ApiError(status_code=404, code=404, message="No downloadable files found")

        archive_name = f"fileflash-download-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.zip"
        tmp = tempfile.NamedTemporaryFile(prefix="fileflash-download-", suffix=".zip", delete=False)
        tmp_path = tmp.name
        tmp.close()

        try:
            with zipfile.ZipFile(tmp_path, mode="w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
                for _file_row, storage_object, zip_path in plan.files:
                    with archive.open(zip_path, mode="w") as entry:
                        async for chunk in self.storage.iter_object(
                            bucket_name=storage_object.bucket_name,
                            object_key=storage_object.object_key,
                        ):
                            entry.write(chunk)
        except Exception as exc:  # noqa: BLE001
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise ApiError(status_code=500, code=500, message=f"Failed to create download archive: {exc}") from exc

        return tmp_path, archive_name

    async def delete_file(self, *, user_id: int, file_id: str) -> DeleteFileResponse:
        file_row, deleted_at = await self._soft_delete_file_record(user_id=user_id, file_id=file_id)
        await self.db.commit()
        return DeleteFileResponse(
            file_id=str(file_row.file_id),
            file_name=file_row.file_name,
            deleted_at=deleted_at,
        )

    async def delete_folder(self, *, user_id: int, folder_id: str) -> DeleteFolderResponse:
        folder_row, deleted_at = await self._soft_delete_folder_record(user_id=user_id, folder_id=folder_id)
        await self.db.commit()
        return DeleteFolderResponse(
            folder_id=str(folder_row.folder_id),
            folder_name=folder_row.folder_name,
            deleted_at=deleted_at,
        )

    async def list_recycle_bin(self, *, user_id: int, query: GetRecycleBinQuery) -> PaginatedData[RecycleBinItem]:
        now = datetime.now(UTC)
        file_rows = (
            await self.db.execute(
                select(File).where(
                    and_(
                        File.owner_id == user_id,
                        File.status == FileStatus.DELETED,
                        File.deleted_at.is_not(None),
                    )
                )
            )
        ).scalars().all()
        folder_rows = (
            await self.db.execute(
                select(Folder).where(
                    and_(
                        Folder.owner_id == user_id,
                        Folder.status == FolderStatus.DELETED,
                        Folder.deleted_at.is_not(None),
                    )
                )
            )
        ).scalars().all()

        recycle_items: list[RecycleBinItem] = []
        if query.item_type in (None, "file"):
            for row in file_rows:
                deleted_at = row.deleted_at or now
                recycle_items.append(
                    RecycleBinItem(
                        item_type="file",
                        id=str(row.file_id),
                        name=row.file_name,
                        original_path=await self._build_folder_path_any_status(user_id=user_id, folder_id=int(row.folder_id)),
                        size=int(row.file_size or 0),
                        mime_type=row.mime_type,
                        deleted_at=deleted_at,
                        auto_delete_at=deleted_at + timedelta(days=_RECYCLE_RETENTION_DAYS),
                        days_until_permanent_delete=self._days_until_permanent_delete(deleted_at, now),
                        can_restore=True,
                        restore_conflicts=False,
                    )
                )
        if query.item_type in (None, "folder"):
            for row in folder_rows:
                deleted_at = row.deleted_at or now
                recycle_items.append(
                    RecycleBinItem(
                        item_type="folder",
                        id=str(row.folder_id),
                        name=row.folder_name,
                        original_path=await self._build_folder_path_any_status(
                            user_id=user_id,
                            folder_id=int(row.parent_folder_id) if row.parent_folder_id else None,
                        ),
                        size=int(row.cached_size or 0),
                        mime_type="inode/directory",
                        folder_id=str(row.parent_folder_id) if row.parent_folder_id is not None else None,
                        folder_name=None,
                        deleted_at=deleted_at,
                        auto_delete_at=deleted_at + timedelta(days=_RECYCLE_RETENTION_DAYS),
                        days_until_permanent_delete=self._days_until_permanent_delete(deleted_at, now),
                        can_restore=True,
                        restore_conflicts=False,
                    )
                )

        recycle_items.sort(key=lambda item: item.deleted_at, reverse=True)
        total = len(recycle_items)
        page = query.page
        per_page = query.per_page
        offset = (page - 1) * per_page
        return self._paginate(recycle_items[offset : offset + per_page], total, page, per_page)

    async def restore_recycle_item(
        self,
        *,
        user_id: int,
        item_id: str,
        payload: RestoreRecycleItemRequest,
    ) -> RestoreRecycleItemResponse:
        async def _operation() -> RestoreRecycleItemResponse:
            await apply_local_lock_timeout(self.db)
            if payload.item_type == "file":
                file_row = await self._get_deleted_file(user_id=user_id, file_id=item_id, for_update=True)
                target_folder_id = await self._resolve_restore_target_folder_id(
                    user_id=user_id,
                    original_folder_id=int(file_row.folder_id),
                    requested_target_folder_id=payload.target_folder_id,
                )
                final_name = await self._next_available_file_name(
                    user_id=user_id,
                    folder_id=target_folder_id,
                    original_name=file_row.file_name,
                    exclude_file_id=int(file_row.file_id),
                )
                now = datetime.now(UTC)
                file_row.status = FileStatus.ACTIVE
                file_row.folder_id = target_folder_id
                file_row.file_name = final_name
                file_row.deleted_at = None
                file_row.deleted_by = None
                file_row.restored_at = now
                file_row.updated_at = now
                await self.db.commit()
                return RestoreRecycleItemResponse(
                    item_type="file",
                    id=str(file_row.file_id),
                    name=file_row.file_name,
                    restored_to=str(target_folder_id),
                    restored_at=now,
                )

            restored_name, restored_at, restored_to = await self._restore_deleted_folder(
                user_id=user_id,
                folder_id=item_id,
                requested_target_folder_id=payload.target_folder_id,
            )
            await self.db.commit()
            return RestoreRecycleItemResponse(
                item_type="folder",
                id=item_id,
                name=restored_name,
                restored_to=restored_to,
                restored_at=restored_at,
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

    async def permanent_delete_recycle_item(
        self,
        *,
        user_id: int,
        item_id: str,
        item_type: str,
    ) -> PermanentDeleteResponse:
        now = datetime.now(UTC)
        if item_type == "file":
            file_row = await self._get_deleted_file(user_id=user_id, file_id=item_id)
            object_id = int(file_row.storage_object_id)
            file_name = file_row.file_name
            await self.db.delete(file_row)
            await self.db.flush()
            await self._cleanup_storage_object_if_orphan(object_id)
            await self.db.commit()
            return PermanentDeleteResponse(
                item_type="file",
                id=item_id,
                name=file_name,
                permanently_deleted_at=now,
            )

        if item_type == "folder":
            folder_row = await self._get_deleted_folder(user_id=user_id, folder_id=item_id)
            subtree = await self._collect_folder_subtree_all_status(
                user_id=user_id,
                root_folder_id=int(folder_row.folder_id),
                status=FolderStatus.DELETED,
            )
            object_ids = list(
                await self.db.scalars(
                    select(File.storage_object_id).where(
                        and_(
                            File.owner_id == user_id,
                            File.status == FileStatus.DELETED,
                            File.folder_id.in_(subtree),
                        )
                    )
                )
            )
            folder_name = folder_row.folder_name
            await self.db.delete(folder_row)
            await self.db.flush()
            for object_id in sorted({int(value) for value in object_ids}):
                await self._cleanup_storage_object_if_orphan(object_id)
            await self.db.commit()
            return PermanentDeleteResponse(
                item_type="folder",
                id=item_id,
                name=folder_name,
                permanently_deleted_at=now,
            )

        raise ApiError(status_code=400, code=400, message="itemType must be file or folder")

    async def clear_recycle_bin(self, *, user_id: int) -> ClearRecycleBinResponse:
        now = datetime.now(UTC)
        deleted_files = (
            await self.db.execute(
                select(File).where(
                    and_(
                        File.owner_id == user_id,
                        File.status == FileStatus.DELETED,
                    )
                )
            )
        ).scalars().all()
        deleted_folders = (
            await self.db.execute(
                select(Folder).where(
                    and_(
                        Folder.owner_id == user_id,
                        Folder.status == FolderStatus.DELETED,
                    )
                )
            )
        ).scalars().all()

        object_ids = sorted({int(row.storage_object_id) for row in deleted_files})

        await self.db.execute(
            delete(File).where(
                and_(
                    File.owner_id == user_id,
                    File.status == FileStatus.DELETED,
                )
            )
        )
        await self.db.execute(
            delete(Folder).where(
                and_(
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.DELETED,
                )
            )
        )
        await self.db.flush()

        total_freed = 0
        for object_id in object_ids:
            total_freed += await self._cleanup_storage_object_if_orphan(object_id)

        await self.db.commit()
        return ClearRecycleBinResponse(
            files_deleted=len(deleted_files),
            folders_deleted=len(deleted_folders),
            total_storage_freed=total_freed,
            cleanup_completed_at=now,
        )

    async def list_starred(self, *, user_id: int) -> PaginatedData[ContentItem]:
        file_rows = (
            await self.db.execute(
                select(FavoriteItem.created_at, File, User.username)
                .join(User, User.user_id == File.owner_id)
                .join(
                    FavoriteItem,
                    and_(
                        FavoriteItem.file_id == File.file_id,
                        FavoriteItem.user_id == user_id,
                        FavoriteItem.item_type == FavoriteItemType.FILE,
                    ),
                )
                .where(
                    and_(
                        File.owner_id == user_id,
                        File.status == FileStatus.ACTIVE,
                        File.is_latest.is_(True),
                    )
                )
            )
        ).all()

        folder_rows = (
            await self.db.execute(
                select(FavoriteItem.created_at, Folder, User.username)
                .join(User, User.user_id == Folder.owner_id)
                .join(
                    FavoriteItem,
                    and_(
                        FavoriteItem.folder_id == Folder.folder_id,
                        FavoriteItem.user_id == user_id,
                        FavoriteItem.item_type == FavoriteItemType.FOLDER,
                    ),
                )
                .where(and_(Folder.owner_id == user_id, Folder.status == FolderStatus.ACTIVE))
            )
        ).all()

        media_optimization_map = await self._load_media_optimization_map([f for _, f, _ in file_rows])
        starred_items: list[tuple[datetime, ContentItem]] = []
        for starred_at, f, username in file_rows:
            starred_items.append(
                (
                    starred_at,
                    self._to_file_item(
                        f,
                        username,
                        is_starred=True,
                        media_optimization=media_optimization_map.get(int(f.file_id)),
                    ),
                )
            )
        for starred_at, folder, username in folder_rows:
            starred_items.append((starred_at, self._to_folder_item(folder, username, is_starred=True)))

        starred_items.sort(key=lambda entry: (entry[0], entry[1].id), reverse=True)
        items = [item for _, item in starred_items]
        return self._paginate(items, len(items), 1, max(len(items), 1))

    async def move_file(self, *, user_id: int, file_id: str, payload: MoveFileRequest) -> MoveFileResponse:
        async def _operation() -> MoveFileResponse:
            await apply_local_lock_timeout(self.db)
            moved = await self._move_file_record(
                user_id=user_id,
                file_id=file_id,
                target_folder_id=payload.target_folder_id,
                share_handling=payload.share_handling,
            )
            await self.db.commit()
            return moved

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

    async def batch_files(self, *, user_id: int, payload: BatchFilesRequest) -> BatchFilesResponse:
        file_ids = list(dict.fromkeys(payload.file_ids))
        folder_ids = list(dict.fromkeys(payload.folder_ids))

        if not file_ids and not folder_ids:
            raise ApiError(status_code=400, code=400, message="At least one fileId or folderId is required")

        if payload.action == "move" and not payload.target_folder_id:
            raise ApiError(status_code=400, code=400, message="targetFolderId is required for move action")

        if payload.action not in {"move", "delete"}:
            raise ApiError(status_code=400, code=400, message="Only move and delete actions are currently supported")

        results: list[BatchMoveItemResult] = []
        succeeded = 0

        for current_file_id in file_ids:
            try:
                if payload.action == "move":
                    moved = await self._move_file_record(
                        user_id=user_id,
                        file_id=current_file_id,
                        target_folder_id=payload.target_folder_id or "root",
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
                else:
                    deleted, deleted_at = await self._soft_delete_file_record(user_id=user_id, file_id=current_file_id)
                    succeeded += 1
                    results.append(
                        BatchMoveItemResult(
                            item_type="file",
                            item_id=str(deleted.file_id),
                            success=True,
                            final_name=deleted.file_name,
                            moved_at=deleted_at,
                            share_handling="keep",
                            revoked_share_count=0,
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
                if payload.action == "move":
                    moved = await self._move_folder_record(
                        user_id=user_id,
                        folder_id=current_folder_id,
                        target_parent_id=payload.target_folder_id or "root",
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
                else:
                    deleted, deleted_at = await self._soft_delete_folder_record(user_id=user_id, folder_id=current_folder_id)
                    succeeded += 1
                    results.append(
                        BatchMoveItemResult(
                            item_type="folder",
                            item_id=str(deleted.folder_id),
                            success=True,
                            final_name=deleted.folder_name,
                            moved_at=deleted_at,
                            share_handling="keep",
                            revoked_share_count=0,
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
        file_row = await self._get_active_file(user_id=user_id, file_id=file_id, for_update=True)
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
        folder_row = await self._get_active_folder(user_id=user_id, folder_id=folder_id, for_update=True)
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

    async def _get_active_file(self, *, user_id: int, file_id: str, for_update: bool = False) -> File:
        fid = self._parse_id(file_id, "fileId")
        statement = select(File).where(
            and_(
                File.file_id == fid,
                File.owner_id == user_id,
                File.status == FileStatus.ACTIVE,
                File.is_latest.is_(True),
            )
        )
        if for_update:
            statement = statement.with_for_update()
        file_row = await self.db.scalar(statement)
        if file_row is None:
            raise ApiError(status_code=404, code=404, message="File not found")
        return file_row

    async def _get_active_folder(self, *, user_id: int, folder_id: str, for_update: bool = False) -> Folder:
        fid = self._parse_id(folder_id, "folderId")
        statement = select(Folder).where(
            and_(
                Folder.folder_id == fid,
                Folder.owner_id == user_id,
                Folder.status == FolderStatus.ACTIVE,
            )
        )
        if for_update:
            statement = statement.with_for_update()
        folder_row = await self.db.scalar(statement)
        if folder_row is None:
            raise ApiError(status_code=404, code=404, message="Folder not found")
        return folder_row

    async def _get_deleted_file(self, *, user_id: int, file_id: str, for_update: bool = False) -> File:
        fid = self._parse_id(file_id, "fileId")
        statement = select(File).where(
            and_(
                File.file_id == fid,
                File.owner_id == user_id,
                File.status == FileStatus.DELETED,
            )
        )
        if for_update:
            statement = statement.with_for_update()
        file_row = await self.db.scalar(statement)
        if file_row is None:
            raise ApiError(status_code=404, code=404, message="File not found in recycle bin")
        return file_row

    async def _get_deleted_folder(self, *, user_id: int, folder_id: str, for_update: bool = False) -> Folder:
        fid = self._parse_id(folder_id, "folderId")
        statement = select(Folder).where(
            and_(
                Folder.folder_id == fid,
                Folder.owner_id == user_id,
                Folder.status == FolderStatus.DELETED,
            )
        )
        if for_update:
            statement = statement.with_for_update()
        folder_row = await self.db.scalar(statement)
        if folder_row is None:
            raise ApiError(status_code=404, code=404, message="Folder not found in recycle bin")
        return folder_row

    async def _soft_delete_file_record(self, *, user_id: int, file_id: str) -> tuple[File, datetime]:
        file_row = await self._get_active_file(user_id=user_id, file_id=file_id)
        deleted_at = datetime.now(UTC)
        file_row.status = FileStatus.DELETED
        file_row.deleted_by = user_id
        file_row.deleted_at = deleted_at
        file_row.restored_at = None
        file_row.updated_at = deleted_at
        return file_row, deleted_at

    async def _soft_delete_folder_record(self, *, user_id: int, folder_id: str) -> tuple[Folder, datetime]:
        folder_row = await self._get_active_folder(user_id=user_id, folder_id=folder_id)
        if folder_row.folder_type == FolderType.ROOT:
            raise ApiError(status_code=400, code=400, message="Root folder cannot be deleted")

        folder_ids, file_ids = await self._collect_folder_subtree(
            user_id=user_id,
            root_folder_id=int(folder_row.folder_id),
        )
        deleted_at = datetime.now(UTC)

        if file_ids:
            await self.db.execute(
                update(File)
                .where(
                    and_(
                        File.owner_id == user_id,
                        File.file_id.in_(file_ids),
                        File.status == FileStatus.ACTIVE,
                    )
                )
                .values(
                    status=FileStatus.DELETED,
                    deleted_by=user_id,
                    deleted_at=deleted_at,
                    restored_at=None,
                    updated_at=deleted_at,
                )
            )

        if folder_ids:
            await self.db.execute(
                update(Folder)
                .where(
                    and_(
                        Folder.owner_id == user_id,
                        Folder.folder_id.in_(folder_ids),
                        Folder.status == FolderStatus.ACTIVE,
                    )
                )
                .values(
                    status=FolderStatus.DELETED,
                    deleted_by=user_id,
                    deleted_at=deleted_at,
                    restored_at=None,
                    updated_at=deleted_at,
                )
            )

        return folder_row, deleted_at

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

    async def _resolve_restore_target_folder_id(
        self,
        *,
        user_id: int,
        original_folder_id: int,
        requested_target_folder_id: str | None,
    ) -> int:
        if requested_target_folder_id:
            return await self._resolve_folder_id(user_id, requested_target_folder_id)

        existing_original = await self.db.scalar(
            select(Folder.folder_id).where(
                and_(
                    Folder.folder_id == original_folder_id,
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if existing_original is not None:
            return int(existing_original)

        return await self._resolve_folder_id(user_id, "root")

    async def _restore_deleted_folder(
        self,
        *,
        user_id: int,
        folder_id: str,
        requested_target_folder_id: str | None,
    ) -> tuple[str, datetime, str]:
        folder_row = await self._get_deleted_folder(user_id=user_id, folder_id=folder_id, for_update=True)
        subtree_ids = await self._collect_folder_subtree_all_status(
            user_id=user_id,
            root_folder_id=int(folder_row.folder_id),
            status=FolderStatus.DELETED,
        )
        if not subtree_ids:
            raise ApiError(status_code=404, code=404, message="Folder not found in recycle bin")

        if requested_target_folder_id:
            target_parent_id = await self._resolve_folder_id(user_id, requested_target_folder_id)
        else:
            if folder_row.parent_folder_id is not None:
                parent_active = await self.db.scalar(
                    select(Folder.folder_id).where(
                        and_(
                            Folder.folder_id == int(folder_row.parent_folder_id),
                            Folder.owner_id == user_id,
                            Folder.status == FolderStatus.ACTIVE,
                        )
                    )
                )
                target_parent_id = int(parent_active) if parent_active is not None else await self._resolve_folder_id(user_id, "root")
            else:
                target_parent_id = await self._resolve_folder_id(user_id, "root")

        restored_at = datetime.now(UTC)
        final_root_name = await self._next_available_folder_name(
            user_id=user_id,
            parent_folder_id=target_parent_id,
            original_name=folder_row.folder_name,
            exclude_folder_id=int(folder_row.folder_id),
        )
        folder_row.parent_folder_id = target_parent_id
        folder_row.folder_name = final_root_name
        folder_row.status = FolderStatus.ACTIVE
        folder_row.deleted_at = None
        folder_row.deleted_by = None
        folder_row.restored_at = restored_at
        folder_row.updated_at = restored_at

        descendants = [folder_id for folder_id in subtree_ids if folder_id != int(folder_row.folder_id)]
        if descendants:
            await self.db.execute(
                update(Folder)
                .where(
                    and_(
                        Folder.owner_id == user_id,
                        Folder.folder_id.in_(descendants),
                        Folder.status == FolderStatus.DELETED,
                    )
                )
                .values(
                    status=FolderStatus.ACTIVE,
                    deleted_at=None,
                    deleted_by=None,
                    restored_at=restored_at,
                    updated_at=restored_at,
                )
            )

        await self.db.execute(
            update(File)
            .where(
                and_(
                    File.owner_id == user_id,
                    File.status == FileStatus.DELETED,
                    File.folder_id.in_(subtree_ids),
                )
            )
            .values(
                status=FileStatus.ACTIVE,
                deleted_at=None,
                deleted_by=None,
                restored_at=restored_at,
                updated_at=restored_at,
            )
        )

        restored_files = list(
            await self.db.scalars(
                select(File).where(
                    and_(
                        File.owner_id == user_id,
                        File.status == FileStatus.ACTIVE,
                        File.folder_id.in_(subtree_ids),
                    )
                )
            )
        )
        for row in restored_files:
            row.file_name = await self._next_available_file_name(
                user_id=user_id,
                folder_id=int(row.folder_id),
                original_name=row.file_name,
                exclude_file_id=int(row.file_id),
            )
            row.updated_at = restored_at

        return final_root_name, restored_at, str(target_parent_id)

    async def _collect_folder_subtree_all_status(
        self,
        *,
        user_id: int,
        root_folder_id: int,
        status: FolderStatus,
    ) -> list[int]:
        descendants = (
            select(Folder.folder_id)
            .where(
                and_(
                    Folder.folder_id == root_folder_id,
                    Folder.owner_id == user_id,
                    Folder.status == status,
                )
            )
            .cte(name="recycle_descendants", recursive=True)
        )
        descendants = descendants.union_all(
            select(Folder.folder_id).where(
                and_(
                    Folder.parent_folder_id == descendants.c.folder_id,
                    Folder.owner_id == user_id,
                    Folder.status == status,
                )
            )
        )
        return list(await self.db.scalars(select(descendants.c.folder_id)))

    async def _build_active_subtree_paths(self, *, user_id: int, root_folder_id: int) -> dict[int, str]:
        root_folder = await self.db.scalar(
            select(Folder).where(
                and_(
                    Folder.folder_id == root_folder_id,
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if root_folder is None:
            return {}

        descendants = (
            select(
                Folder.folder_id,
                Folder.parent_folder_id,
                Folder.folder_name,
            )
            .where(
                and_(
                    Folder.folder_id == root_folder_id,
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
            .cte(name="download_descendants", recursive=True)
        )
        descendants = descendants.union_all(
            select(
                Folder.folder_id,
                Folder.parent_folder_id,
                Folder.folder_name,
            ).where(
                and_(
                    Folder.parent_folder_id == descendants.c.folder_id,
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        rows = (
            await self.db.execute(
                select(descendants.c.folder_id, descendants.c.parent_folder_id, descendants.c.folder_name)
            )
        ).all()

        children_map: dict[int, list[tuple[int, str]]] = {}
        for folder_id, parent_folder_id, folder_name in rows:
            if parent_folder_id is None:
                continue
            children_map.setdefault(int(parent_folder_id), []).append((int(folder_id), str(folder_name)))

        path_map: dict[int, str] = {int(root_folder.folder_id): root_folder.folder_name}
        stack = [int(root_folder.folder_id)]
        while stack:
            parent_id = stack.pop()
            parent_path = path_map[parent_id]
            for child_id, child_name in children_map.get(parent_id, []):
                path_map[child_id] = f"{parent_path}/{child_name}"
                stack.append(child_id)
        return path_map

    async def _build_folder_path_any_status(self, *, user_id: int, folder_id: int | None) -> str:
        if folder_id is None:
            return "My Files"

        parts: list[str] = []
        current_id: int | None = folder_id
        while current_id is not None:
            folder = await self.db.scalar(
                select(Folder).where(
                    and_(
                        Folder.folder_id == current_id,
                        Folder.owner_id == user_id,
                    )
                )
            )
            if folder is None:
                break
            parts.append(folder.folder_name)
            current_id = int(folder.parent_folder_id) if folder.parent_folder_id is not None else None
        if not parts:
            return "My Files"
        parts.reverse()
        return "/".join(parts)

    async def _cleanup_storage_object_if_orphan(self, object_id: int) -> int:
        remaining_refs = await self.db.scalar(
            select(func.count()).select_from(File).where(File.storage_object_id == object_id)
        )
        if (remaining_refs or 0) > 0:
            return 0

        storage_object = await self.db.get(StorageObject, object_id)
        if storage_object is None:
            return 0

        if self.storage is None:
            raise ApiError(status_code=503, code=503, message="Object storage is unavailable")

        try:
            await self.storage.remove_object(
                bucket_name=storage_object.bucket_name,
                object_key=storage_object.object_key,
            )
        except Exception as exc:  # noqa: BLE001
            raise ApiError(
                status_code=503,
                code=503,
                message=f"Failed to remove object from storage: {exc}",
            ) from exc

        deleted_at = datetime.now(UTC)
        storage_object.upload_status = UploadStatus.DELETED
        storage_object.deleted_at = deleted_at
        storage_object.updated_at = deleted_at
        return int(storage_object.object_size or 0)

    @staticmethod
    def _days_until_permanent_delete(deleted_at: datetime, now: datetime) -> int:
        auto_delete_at = deleted_at + timedelta(days=_RECYCLE_RETENTION_DAYS)
        remaining_seconds = (auto_delete_at - now).total_seconds()
        if remaining_seconds <= 0:
            return 0
        return int((remaining_seconds + 24 * 3600 - 1) // (24 * 3600))

    def _dedupe_ids(self, raw_ids: list[str], field_name: str) -> list[int]:
        parsed: list[int] = []
        seen: set[int] = set()
        for raw in raw_ids:
            value = self._parse_id(raw, field_name)
            if value in seen:
                continue
            parsed.append(value)
            seen.add(value)
        return parsed

    @staticmethod
    def _parse_range_header(range_header: str | None, file_size: int) -> tuple[int, int] | None:
        if not range_header:
            return None

        value = range_header.strip()
        if not value.lower().startswith("bytes="):
            raise ApiError(status_code=416, code=416, message="Invalid Range header")

        spec = value[6:].strip()
        if "," in spec:
            raise ApiError(status_code=416, code=416, message="Multiple ranges are not supported")

        if spec.startswith("-"):
            suffix_part = spec[1:].strip()
            if not suffix_part.isdigit():
                raise ApiError(status_code=416, code=416, message="Invalid Range header")
            suffix = int(suffix_part)
            if suffix <= 0:
                raise ApiError(status_code=416, code=416, message="Invalid Range header")
            start = max(file_size - suffix, 0)
            end = file_size - 1
            return start, end

        if "-" not in spec:
            raise ApiError(status_code=416, code=416, message="Invalid Range header")

        start_part, end_part = spec.split("-", 1)
        if not start_part.strip().isdigit():
            raise ApiError(status_code=416, code=416, message="Invalid Range header")
        start = int(start_part.strip())
        end = file_size - 1
        if end_part.strip():
            if not end_part.strip().isdigit():
                raise ApiError(status_code=416, code=416, message="Invalid Range header")
            end = int(end_part.strip())

        if start < 0 or start >= file_size or end < start:
            raise ApiError(status_code=416, code=416, message="Requested range is not satisfiable")

        if end >= file_size:
            end = file_size - 1
        return start, end

    @staticmethod
    def _safe_zip_path(path: str) -> str:
        normalized = path.replace("\\", "/").lstrip("/")
        segments = [segment for segment in normalized.split("/") if segment not in {"", ".", ".."}]
        return "/".join(segments) or "file"

    @staticmethod
    def _build_attachment_header(filename: str) -> str:
        return FileService._build_content_disposition_header(filename, disposition="attachment")

    @staticmethod
    def _build_content_disposition_header(
        filename: str,
        *,
        disposition: Literal["attachment", "inline"],
    ) -> str:
        return build_content_disposition(filename, disposition=disposition)

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

    async def _get_file_favorite(self, *, user_id: int, file_id: int) -> FavoriteItem | None:
        return await self.db.scalar(
            select(FavoriteItem).where(
                and_(
                    FavoriteItem.user_id == user_id,
                    FavoriteItem.item_type == FavoriteItemType.FILE,
                    FavoriteItem.file_id == file_id,
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
        for file_row in files:
            media = self._parse_media_optimization(by_object_id.get(int(file_row.storage_object_id)))
            if media is not None:
                result[int(file_row.file_id)] = media
        return result

    async def _load_file_media_optimization(self, file_row: File) -> MediaOptimization | None:
        metadata_row = await self.db.scalar(
            select(FileMediaMetadata)
            .where(FileMediaMetadata.source_object_id == int(file_row.storage_object_id))
            .limit(1)
        )
        if not isinstance(metadata_row, FileMediaMetadata):
            return None
        return self._parse_media_optimization(metadata_row)

    def _parse_media_optimization(self, metadata_row: FileMediaMetadata | None) -> MediaOptimization | None:
        if metadata_row is None:
            return None
        extra = metadata_row.extra_metadata or {}
        transcode = extra.get("transcode")
        if not isinstance(transcode, dict):
            return None

        status = str(transcode.get("status") or "").strip().lower()
        media_type = str(transcode.get("mediaType") or "").strip().lower()
        updated_at_raw = transcode.get("updatedAt")
        optimized_mime_type = transcode.get("optimizedMimeType")
        if status not in {"queued", "running", "ready", "failed"}:
            return None
        if media_type not in {"audio", "video"}:
            return None

        updated_at = self._parse_datetime(updated_at_raw) or metadata_row.extracted_at
        if not updated_at:
            return None

        return MediaOptimization(
            status=status,  # type: ignore[arg-type]
            media_type=media_type,  # type: ignore[arg-type]
            optimized_mime_type=str(optimized_mime_type) if optimized_mime_type else None,
            updated_at=updated_at,
        )

    async def _resolve_stream_storage_object(
        self,
        *,
        file_row: File,
        prefer_optimized: bool,
    ) -> ResolvedStreamObject | None:
        source_object = await self.db.get(StorageObject, int(file_row.storage_object_id))
        if source_object is None:
            return None
        if not prefer_optimized:
            return ResolvedStreamObject(storage_object=source_object)

        metadata_row = await self.db.scalar(
            select(FileMediaMetadata)
            .where(FileMediaMetadata.source_object_id == int(file_row.storage_object_id))
            .limit(1)
        )
        if not isinstance(metadata_row, FileMediaMetadata):
            return ResolvedStreamObject(storage_object=source_object)
        transcode = (metadata_row.extra_metadata or {}).get("transcode")
        if not isinstance(transcode, dict):
            return ResolvedStreamObject(storage_object=source_object)
        if str(transcode.get("status") or "").strip().lower() != TRANSCODE_READY_STATUS:
            return ResolvedStreamObject(storage_object=source_object)

        bucket_name = str(transcode.get("optimizedBucketName") or "").strip()
        object_key = str(transcode.get("optimizedObjectKey") or "").strip()
        if not bucket_name or not object_key:
            return ResolvedStreamObject(storage_object=source_object)

        optimized_mime_type = str(transcode.get("optimizedMimeType") or "").strip() or None

        optimized_object = await self.db.scalar(
            select(StorageObject)
            .where(
                and_(
                    StorageObject.bucket_name == bucket_name,
                    StorageObject.object_key == object_key,
                    StorageObject.upload_status == UploadStatus.ACTIVE,
                )
            )
            .limit(1)
        )
        if isinstance(optimized_object, StorageObject):
            return ResolvedStreamObject(
                storage_object=optimized_object,
                content_type_override=optimized_mime_type or optimized_object.content_type,
            )

        if self.storage is None:
            return ResolvedStreamObject(storage_object=source_object)
        exists = await self.storage.object_exists(bucket_name=bucket_name, object_key=object_key)
        if not exists:
            return ResolvedStreamObject(storage_object=source_object)

        stat = await self.storage.stat_object(bucket_name=bucket_name, object_key=object_key)
        created = StorageObject(
            bucket_name=bucket_name,
            object_key=object_key,
            object_size=int(stat.size),
            etag=stat.etag,
            version_id=stat.version_id,
            content_type=stat.content_type,
            upload_status=UploadStatus.ACTIVE,
        )
        self.db.add(created)
        await self.db.flush()
        return ResolvedStreamObject(
            storage_object=created,
            content_type_override=optimized_mime_type or created.content_type,
        )

    @staticmethod
    def _parse_datetime(raw: object) -> datetime | None:
        if raw is None:
            return None
        if isinstance(raw, datetime):
            return raw
        text = str(raw).strip()
        if not text:
            return None
        try:
            value = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

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
