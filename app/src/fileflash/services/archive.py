from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..models.enums import FileStatus, FolderStatus
from ..models.tables_storage import File, Folder, StorageObject
from ..schemas.archive import ArchiveExtractRequest
from .background_jobs import BackgroundJobService

SupportedArchiveConflictStrategy = Literal["rename", "overwrite", "skip"]


class ArchiveService:
    def __init__(self, *, db: AsyncSession, jobs: BackgroundJobService) -> None:
        self.db = db
        self.jobs = jobs

    async def create_preview_job(self, *, user_id: int, file_id: str) -> object:
        file_row, storage_row = await self._load_file_and_storage(user_id=user_id, file_id=file_id)
        self._validate_archive_name(file_row.file_name)

        payload = {
            "requestedBy": user_id,
            "fileId": str(file_row.file_id),
            "fileName": file_row.file_name,
            "bucketName": storage_row.bucket_name,
            "objectKey": storage_row.object_key,
        }
        return await self.jobs.enqueue(
            self.db,
            task_type="task.archive_preview",
            payload=payload,
            idempotency_key=f"file:{file_row.file_id}:archive_preview:v1",
            requested_by=user_id,
        )

    async def create_extract_job(
        self,
        *,
        user_id: int,
        file_id: str,
        payload: ArchiveExtractRequest,
    ) -> object:
        file_row, storage_row = await self._load_file_and_storage(user_id=user_id, file_id=file_id)
        self._validate_archive_name(file_row.file_name)

        await self._validate_target_folder(user_id=user_id, target_folder_id=payload.target_folder_id)

        conflict_strategy: SupportedArchiveConflictStrategy = payload.conflict_strategy or "rename"
        if conflict_strategy not in ("rename", "overwrite", "skip"):
            raise ApiError(status_code=400, code=400, message="conflictStrategy must be rename, overwrite, or skip")

        job_payload: dict[str, Any] = {
            "requestedBy": user_id,
            "fileId": str(file_row.file_id),
            "fileName": file_row.file_name,
            "bucketName": storage_row.bucket_name,
            "objectKey": storage_row.object_key,
            "targetFolderId": payload.target_folder_id,
            "createSubfolder": bool(payload.create_subfolder),
            "subfolderName": payload.subfolder_name,
            "conflictStrategy": conflict_strategy,
        }
        return await self.jobs.enqueue(
            self.db,
            task_type="task.archive_extract",
            payload=job_payload,
            requested_by=user_id,
        )

    async def _load_file_and_storage(self, *, user_id: int, file_id: str) -> tuple[File, StorageObject]:
        try:
            parsed_id = int(file_id)
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message="Invalid fileId") from exc

        row = await self.db.execute(
            select(File, StorageObject)
            .join(StorageObject, File.storage_object_id == StorageObject.object_id)
            .where(
                and_(
                    File.file_id == parsed_id,
                    File.owner_id == user_id,
                    File.status == FileStatus.ACTIVE,
                )
            )
            .limit(1)
        )
        pair = row.first()
        if pair is None:
            raise ApiError(status_code=404, code=404, message="File not found")
        file_row, storage_row = pair
        return file_row, storage_row

    async def _validate_target_folder(self, *, user_id: int, target_folder_id: str) -> None:
        if target_folder_id == "root":
            return

        try:
            parsed = int(target_folder_id)
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message="Invalid targetFolderId") from exc

        folder = await self.db.scalar(
            select(Folder.folder_id).where(
                and_(
                    Folder.folder_id == parsed,
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if folder is None:
            raise ApiError(status_code=404, code=404, message="Target folder not found")

    def _validate_archive_name(self, file_name: str) -> None:
        if not self._is_supported_archive_name(file_name):
            raise ApiError(status_code=400, code=400, message="Unsupported archive format")

    @staticmethod
    def _is_supported_archive_name(file_name: str) -> bool:
        lower = (file_name or "").strip().lower()
        return any(
            lower.endswith(ext)
            for ext in (
                ".zip",
                ".7z",
                ".tar",
                ".tar.gz",
                ".tgz",
                ".gz",
            )
        )
