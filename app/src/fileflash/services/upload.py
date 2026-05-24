from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ApiError
from ..core.mime import DEFAULT_MIME_TYPE, resolve_file_mime_type
from ..core.settings import Settings
from ..db.transaction import (
    apply_local_lock_timeout,
    is_retryable_database_error,
    is_unique_violation_error,
    run_with_transaction_retry,
    to_retryable_concurrency_error,
)
from ..models.enums import (
    FileStatus,
    FolderStatus,
    FolderType,
    UploadMode,
    UploadPartStatus,
    UploadStatus,
    UploadTaskStatus,
)
from ..models.tables_storage import File, FileMediaMetadata, Folder, StorageObject, UploadTask, UploadTaskPart
from ..models.tables_worker import BackgroundJob
from ..s3.minio_client import MinioObjectStorageClient, ObjectStorageError
from ..schemas.file import (
    MergeChunksRequest,
    MergeChunksResponse,
    UploadCancelResponse,
    UploadPreflightRequest,
    UploadPreflightResponse,
)
from .background_jobs import BackgroundJobService

logger = logging.getLogger(__name__)

TRANSCODE_PROFILE_VERSION = "mp4-v1"


class UploadService:
    def __init__(
        self,
        *,
        db: AsyncSession,
        settings: Settings,
        storage: MinioObjectStorageClient,
        jobs: BackgroundJobService | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.storage = storage
        self.jobs = jobs

    async def preflight(self, *, user_id: int, payload: UploadPreflightRequest) -> UploadPreflightResponse:
        async def _operation() -> UploadPreflightResponse:
            object_hash, hash_algorithm = self._normalize_hash(payload.file_hash)
            self._validate_upload_size(payload.file_size)
            await apply_local_lock_timeout(self.db)
            try:
                await self.storage.ensure_bucket()
            except ObjectStorageError as exc:
                logger.exception(
                    "Object storage unavailable during upload preflight for userId=%s",
                    user_id,
                )
                raise ApiError(status_code=503, code=503, message="Object storage unavailable") from exc
            await self._cleanup_expired_tasks(user_id=user_id)

            folder_id = await self._resolve_folder_id(user_id=user_id, parent_id=payload.parent_id)
            resolved_mime_type = resolve_file_mime_type(
                mime_type=payload.mime_type,
                file_ext=self._extract_ext(payload.file_name),
                file_name=payload.file_name,
                default=DEFAULT_MIME_TYPE,
            )

            storage_object = await self._find_storage_object(
                object_hash=object_hash,
                hash_algorithm=hash_algorithm,
                object_size=payload.file_size,
            )
            if storage_object is not None:
                file_row = await self._create_file_from_storage_object(
                    user_id=user_id,
                    folder_id=folder_id,
                    file_name=payload.file_name,
                    mime_type=resolved_mime_type,
                    storage_object=storage_object,
                )
                await self.db.commit()
                return UploadPreflightResponse(status="COMPLETE", file_id=str(file_row.file_id))

            task = await self._find_active_task(
                user_id=user_id,
                object_hash=object_hash,
                total_size=payload.file_size,
            )
            if task is not None:
                if task.status == UploadTaskStatus.INIT:
                    task.status = UploadTaskStatus.UPLOADING
                    await self.db.commit()
                uploaded_indexes = await self._list_uploaded_indexes(task_id=task.task_id)
                return UploadPreflightResponse(
                    status="UPLOADING",
                    upload_id=task.upload_id,
                    chunk_size=task.chunk_size or self._resolved_chunk_size(),
                    uploaded_chunk_indexes=uploaded_indexes,
                )

            now = datetime.now(UTC)
            upload_id = str(uuid4())
            task = UploadTask(
                user_id=user_id,
                folder_id=folder_id,
                file_name=payload.file_name,
                mime_type=resolved_mime_type,
                bucket_name=self.settings.object_storage_bucket,
                object_key=self._build_object_key(user_id=user_id),
                object_hash=object_hash,
                total_size=payload.file_size,
                chunk_size=self._resolved_chunk_size(),
                uploaded_bytes=0,
                upload_id=upload_id,
                upload_mode=UploadMode.MULTIPART,
                status=UploadTaskStatus.UPLOADING,
                expired_at=now + timedelta(seconds=self.settings.upload_session_ttl_seconds),
            )
            self.db.add(task)
            await self.db.commit()
            return UploadPreflightResponse(
                status="UPLOADING",
                upload_id=upload_id,
                chunk_size=task.chunk_size,
                uploaded_chunk_indexes=[],
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

    async def upload_chunk(self, *, user_id: int, upload_id: str, chunk_index: int, chunk_bytes: bytes) -> None:
        if chunk_index < 0:
            raise ApiError(status_code=400, code=400, message="chunkIndex must be >= 0")
        if not chunk_bytes:
            raise ApiError(status_code=400, code=400, message="chunk is empty")

        task = await self._get_task_for_update(user_id=user_id, upload_id=upload_id)
        if task is None:
            raise ApiError(status_code=404, code=404, message="Upload session not found")

        now = datetime.now(UTC)
        if task.expired_at and task.expired_at <= now:
            await self._abort_task(task=task, reason="Upload session expired")
            raise ApiError(status_code=410, code=410, message="Upload session expired")
        if task.status in (UploadTaskStatus.COMPLETED, UploadTaskStatus.ABORTED, UploadTaskStatus.FAILED):
            raise ApiError(status_code=409, code=409, message="Upload session is not writable")

        chunk_size = task.chunk_size or self._resolved_chunk_size()
        total_chunks = max(1, (task.total_size + chunk_size - 1) // chunk_size)
        if chunk_index >= total_chunks:
            raise ApiError(status_code=400, code=400, message="chunkIndex out of range")

        start = chunk_index * chunk_size
        end = min(start + chunk_size, task.total_size)
        expected_size = end - start
        if len(chunk_bytes) != expected_size:
            raise ApiError(
                status_code=400,
                code=400,
                message=f"Invalid chunk size for index {chunk_index}, expected {expected_size}",
            )

        object_key = self._build_part_object_key(task=task, chunk_index=chunk_index)
        checksum = hashlib.sha256(chunk_bytes).hexdigest()

        existing_part = await self.db.scalar(
            select(UploadTaskPart)
            .where(and_(UploadTaskPart.task_id == task.task_id, UploadTaskPart.part_number == chunk_index))
            .with_for_update()
        )
        if (
            existing_part is not None
            and existing_part.status == UploadPartStatus.UPLOADED
            and existing_part.checksum == checksum
            and existing_part.part_size == expected_size
        ):
            return

        try:
            write_result = await self.storage.put_bytes(
                object_key=object_key,
                data=chunk_bytes,
                content_type="application/octet-stream",
            )
        except Exception as exc:  # noqa: BLE001
            if existing_part is not None:
                existing_part.status = UploadPartStatus.FAILED
                existing_part.retry_count += 1
            task.last_error = f"Failed to store chunk {chunk_index}: {exc}"
            await self.db.commit()
            raise ApiError(status_code=500, code=500, message="Failed to store upload chunk") from exc

        if existing_part is None:
            existing_part = UploadTaskPart(
                task_id=task.task_id,
                part_number=chunk_index,
                part_size=expected_size,
                status=UploadPartStatus.UPLOADED,
                etag=write_result.etag,
                checksum=checksum,
                uploaded_at=now,
            )
            self.db.add(existing_part)
        else:
            existing_part.part_size = expected_size
            existing_part.status = UploadPartStatus.UPLOADED
            existing_part.etag = write_result.etag
            existing_part.checksum = checksum
            existing_part.uploaded_at = now

        uploaded_bytes = await self.db.scalar(
            select(func.coalesce(func.sum(UploadTaskPart.part_size), 0)).where(
                and_(
                    UploadTaskPart.task_id == task.task_id,
                    UploadTaskPart.status == UploadPartStatus.UPLOADED,
                )
            )
        )
        task.uploaded_bytes = int(uploaded_bytes or 0)
        task.status = UploadTaskStatus.UPLOADING
        task.last_error = None
        await self.db.commit()

    async def enqueue_merge_job(
        self,
        *,
        user_id: int,
        upload_id: str,
        payload: MergeChunksRequest,
    ) -> BackgroundJob:
        jobs = self.jobs
        if jobs is None:
            raise ApiError(status_code=503, code=503, message="Job queue unavailable")

        # Normalize hash early to keep retries idempotent for equivalent requests.
        normalized_hash, _ = self._normalize_hash(payload.file_hash)
        normalized_payload = MergeChunksRequest(
            file_hash=normalized_hash,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            parent_id=payload.parent_id,
            conflict_strategy=payload.conflict_strategy,
        )
        merge_request_payload = normalized_payload.model_dump(by_alias=True, exclude_none=True)
        job_payload: dict[str, Any] = {
            "userId": user_id,
            "uploadId": upload_id,
            "mergeRequest": merge_request_payload,
        }
        idempotency_key = self._build_merge_job_idempotency_key(
            user_id=user_id,
            upload_id=upload_id,
            merge_request_payload=merge_request_payload,
        )
        return await jobs.enqueue(
            self.db,
            task_type="task.upload_merge",
            payload=job_payload,
            idempotency_key=idempotency_key,
            requested_by=user_id,
        )

    async def execute_merge_job(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        raw_user_id = payload.get("userId")
        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Merge job payload requires valid userId") from exc
        if user_id <= 0:
            raise ValueError("Merge job payload userId must be > 0")

        upload_id = str(payload.get("uploadId") or "").strip()
        if not upload_id:
            raise ValueError("Merge job payload requires uploadId")

        merge_request_raw = payload.get("mergeRequest")
        if not isinstance(merge_request_raw, dict):
            raise ValueError("Merge job payload requires mergeRequest object")
        merge_request = MergeChunksRequest.model_validate(merge_request_raw)
        response = await self.merge_chunks(
            user_id=user_id,
            upload_id=upload_id,
            payload=merge_request,
        )
        return response.model_dump(by_alias=True, mode="json")

    async def merge_chunks(
        self,
        *,
        user_id: int,
        upload_id: str,
        payload: MergeChunksRequest,
    ) -> MergeChunksResponse:
        async def _operation() -> MergeChunksResponse:
            object_hash, hash_algorithm = self._normalize_hash(payload.file_hash)
            resolved_mime_type = resolve_file_mime_type(
                mime_type=payload.mime_type,
                file_ext=self._extract_ext(payload.file_name),
                file_name=payload.file_name,
                default=DEFAULT_MIME_TYPE,
            )
            await apply_local_lock_timeout(self.db)
            task = await self._get_task_for_update(user_id=user_id, upload_id=upload_id)
            if task is None:
                raise ApiError(status_code=404, code=404, message="Upload session not found")
            task_object_hash = self._normalize_task_hash(task.object_hash)

            now = datetime.now(UTC)
            if task.expired_at and task.expired_at <= now:
                await self._abort_task(task=task, reason="Upload session expired")
                raise ApiError(status_code=410, code=410, message="Upload session expired")
            if task.status == UploadTaskStatus.COMPLETED:
                completed = await self._find_completed_file_for_task(task=task)
                if completed is not None:
                    return MergeChunksResponse(
                        file_id=str(completed.file_id),
                        file_name=completed.file_name,
                        file_size=int(completed.file_size),
                        mime_type=resolve_file_mime_type(
                            mime_type=completed.mime_type,
                            file_ext=completed.file_ext,
                            file_name=completed.file_name,
                            default=DEFAULT_MIME_TYPE,
                        ),
                        folder_id=str(completed.folder_id),
                        object_hash=task_object_hash,
                        created_at=completed.created_at,
                        download_url=f"{self.settings.api_v1_prefix}/files/{completed.file_id}/download",
                    )
                raise ApiError(status_code=409, code=409, message="Upload session already completed")
            if task.status in (UploadTaskStatus.ABORTED, UploadTaskStatus.FAILED):
                raise ApiError(status_code=409, code=409, message="Upload session is not mergeable")
            if task_object_hash and task_object_hash != object_hash:
                logger.warning(
                    "Upload merge hash mismatch uploadId=%s userId=%s taskId=%s expectedHash=%s actualHash=%s",
                    upload_id,
                    user_id,
                    task.task_id,
                    task_object_hash,
                    object_hash,
                )
                raise ApiError(status_code=400, code=400, message="fileHash does not match upload session")

            folder_id = await self._resolve_folder_id(user_id=user_id, parent_id=payload.parent_id)
            final_file_name = payload.file_name
            overwrite_target: File | None = None
            conflict = await self._find_conflict_file(user_id=user_id, folder_id=folder_id, file_name=payload.file_name)
            if conflict is not None:
                if payload.conflict_strategy is None:
                    raise ApiError(
                        status_code=409,
                        code=409,
                        message="File name conflict",
                        data=self._build_conflict_data(conflict),
                    )
                if payload.conflict_strategy == "cancel":
                    raise ApiError(
                        status_code=409,
                        code=409,
                        message="Upload cancelled by client",
                        data=self._build_conflict_data(conflict),
                    )
                if payload.conflict_strategy == "rename":
                    final_file_name = await self._next_available_file_name(
                        user_id=user_id,
                        folder_id=folder_id,
                        original_name=payload.file_name,
                    )
                elif payload.conflict_strategy == "overwrite":
                    overwrite_target = conflict

            chunk_size = task.chunk_size or self._resolved_chunk_size()
            expected_chunks = max(1, (task.total_size + chunk_size - 1) // chunk_size)
            parts = list(
                await self.db.scalars(
                    select(UploadTaskPart)
                    .where(
                        and_(
                            UploadTaskPart.task_id == task.task_id,
                            UploadTaskPart.status == UploadPartStatus.UPLOADED,
                        )
                    )
                    .order_by(UploadTaskPart.part_number.asc())
                )
            )

            if len(parts) != expected_chunks:
                logger.warning(
                    "Upload merge incomplete chunks uploadId=%s userId=%s taskId=%s expectedChunks=%s uploadedChunks=%s",
                    upload_id,
                    user_id,
                    task.task_id,
                    expected_chunks,
                    len(parts),
                )
                raise ApiError(status_code=400, code=400, message="Uploaded chunks are incomplete")
            expected_indexes = list(range(expected_chunks))
            actual_indexes = [part.part_number for part in parts]
            if actual_indexes != expected_indexes:
                logger.warning(
                    "Upload merge non-continuous chunks uploadId=%s userId=%s taskId=%s expectedIndexes=%s actualIndexes=%s",
                    upload_id,
                    user_id,
                    task.task_id,
                    expected_indexes,
                    actual_indexes,
                )
                raise ApiError(status_code=400, code=400, message="Uploaded chunk indexes are not continuous")

            source_keys = [self._build_part_object_key(task=task, chunk_index=part.part_number) for part in parts]
            try:
                compose_result = await self.storage.compose_object(object_key=task.object_key, source_keys=source_keys)
                object_stat = await self.storage.stat_object(object_key=task.object_key)
            except Exception as exc:  # noqa: BLE001
                task.status = UploadTaskStatus.FAILED
                task.last_error = f"Failed to compose chunks: {exc}"
                await self.db.commit()
                raise ApiError(status_code=500, code=500, message="Failed to compose uploaded chunks") from exc

            if object_stat.size != task.total_size:
                await self.storage.remove_object(object_key=task.object_key)
                task.status = UploadTaskStatus.FAILED
                task.last_error = "Composed file size mismatch"
                await self.db.commit()
                raise ApiError(status_code=422, code=422, message="Composed file size mismatch")

            actual_hash = await self.storage.compute_object_hash(
                object_key=task.object_key,
                algorithm=hash_algorithm,
            )
            if actual_hash != object_hash:
                await self.storage.remove_object(object_key=task.object_key)
                task.status = UploadTaskStatus.FAILED
                task.last_error = "Composed file hash mismatch"
                await self.db.commit()
                raise ApiError(status_code=422, code=422, message="Composed file hash mismatch")

            storage_object = await self._find_storage_object(
                object_hash=object_hash,
                hash_algorithm=hash_algorithm,
                object_size=task.total_size,
            )
            if storage_object is None:
                storage_object = StorageObject(
                    object_hash=object_hash,
                    hash_algorithm=hash_algorithm,
                    bucket_name=task.bucket_name,
                    object_key=task.object_key,
                    object_size=task.total_size,
                    etag=object_stat.etag or compose_result.etag,
                    version_id=compose_result.version_id,
                    content_type=resolved_mime_type,
                    upload_status=UploadStatus.ACTIVE,
                )
                self.db.add(storage_object)
                await self.db.flush()
            elif storage_object.object_key != task.object_key:
                await self.storage.remove_object(object_key=task.object_key)

            if overwrite_target is not None:
                overwrite_target.status = FileStatus.DELETED
                overwrite_target.deleted_by = user_id
                overwrite_target.deleted_at = now

            file_row = File(
                uploader_id=user_id,
                owner_id=user_id,
                folder_id=folder_id,
                file_name=final_file_name,
                file_ext=self._extract_ext(final_file_name),
                mime_type=resolved_mime_type,
                storage_object_id=storage_object.object_id,
                file_size=task.total_size,
                status=FileStatus.ACTIVE,
            )
            self.db.add(file_row)
            await self.db.flush()

            task.file_name = final_file_name
            task.mime_type = resolved_mime_type
            task.folder_id = folder_id
            task.object_hash = object_hash
            task.status = UploadTaskStatus.COMPLETED
            task.uploaded_bytes = task.total_size
            task.last_error = None
            task.completed_at = now
            await self.db.commit()

            if self._is_transcode_candidate(resolved_mime_type):
                await self._enqueue_transcode_after_merge(
                    user_id=user_id,
                    file_row=file_row,
                    storage_object=storage_object,
                )

            try:
                await self.storage.remove_objects(object_keys=source_keys)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to remove temporary upload chunks for uploadId=%s", upload_id)

            return MergeChunksResponse(
                file_id=str(file_row.file_id),
                file_name=file_row.file_name,
                file_size=file_row.file_size,
                mime_type=resolve_file_mime_type(
                    mime_type=file_row.mime_type,
                    file_ext=file_row.file_ext,
                    file_name=file_row.file_name,
                    default=DEFAULT_MIME_TYPE,
                ),
                folder_id=str(file_row.folder_id),
                object_hash=object_hash,
                created_at=file_row.created_at,
                download_url=f"{self.settings.api_v1_prefix}/files/{file_row.file_id}/download",
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

    async def cancel_upload_session(self, *, user_id: int, upload_id: str) -> UploadCancelResponse:
        task = await self._get_task_for_update(user_id=user_id, upload_id=upload_id)
        if task is None:
            raise ApiError(status_code=404, code=404, message="Upload session not found")
        if task.status == UploadTaskStatus.COMPLETED:
            raise ApiError(status_code=409, code=409, message="Upload session already completed")
        if task.status == UploadTaskStatus.FAILED:
            raise ApiError(status_code=409, code=409, message="Upload session is not cancelable")
        if task.status == UploadTaskStatus.ABORTED:
            return UploadCancelResponse(
                upload_id=upload_id,
                canceled_at=task.updated_at or datetime.now(UTC),
            )

        canceled_at = datetime.now(UTC)
        cleanup_keys = await self._collect_task_cleanup_keys(task=task)
        task.status = UploadTaskStatus.ABORTED
        task.last_error = "Upload canceled by client"
        await self.db.commit()

        if cleanup_keys:
            try:
                await self.storage.remove_objects(object_keys=cleanup_keys)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to cleanup canceled upload temp objects uploadId=%s", upload_id)

        return UploadCancelResponse(upload_id=upload_id, canceled_at=canceled_at)

    async def _cleanup_expired_tasks(self, *, user_id: int) -> None:
        now = datetime.now(UTC)
        expired_tasks = list(
            await self.db.scalars(
                select(UploadTask).where(
                    and_(
                        UploadTask.user_id == user_id,
                        UploadTask.status.in_((UploadTaskStatus.INIT, UploadTaskStatus.UPLOADING)),
                        UploadTask.expired_at.is_not(None),
                        UploadTask.expired_at <= now,
                    )
                )
            )
        )
        if not expired_tasks:
            return

        cleanup_keys: list[str] = []
        for task in expired_tasks:
            task.status = UploadTaskStatus.ABORTED
            task.last_error = "Upload session expired"
            cleanup_keys.extend(await self._collect_task_cleanup_keys(task=task))

        await self.db.commit()
        if cleanup_keys:
            try:
                await self.storage.remove_objects(object_keys=cleanup_keys)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to cleanup expired upload temp objects")

    async def _find_active_task(self, *, user_id: int, object_hash: str, total_size: int) -> UploadTask | None:
        now = datetime.now(UTC)
        return await self.db.scalar(
            select(UploadTask)
            .where(
                and_(
                    UploadTask.user_id == user_id,
                    UploadTask.object_hash == object_hash,
                    UploadTask.total_size == total_size,
                    UploadTask.status.in_((UploadTaskStatus.INIT, UploadTaskStatus.UPLOADING)),
                    or_(UploadTask.expired_at.is_(None), UploadTask.expired_at > now),
                )
            )
            .order_by(UploadTask.created_at.desc())
            .limit(1)
        )

    async def _get_task_for_update(self, *, user_id: int, upload_id: str) -> UploadTask | None:
        return await self.db.scalar(
            select(UploadTask)
            .where(and_(UploadTask.user_id == user_id, UploadTask.upload_id == upload_id))
            .with_for_update()
        )

    async def _find_completed_file_for_task(self, *, task: UploadTask) -> File | None:
        if task.folder_id is None or not task.file_name:
            return None
        return await self.db.scalar(
            select(File)
            .where(
                and_(
                    File.owner_id == task.user_id,
                    File.folder_id == int(task.folder_id),
                    File.file_name == task.file_name,
                    File.status == FileStatus.ACTIVE,
                    File.is_latest.is_(True),
                )
            )
            .order_by(File.file_id.desc())
            .limit(1)
        )

    async def _find_storage_object(
        self,
        *,
        object_hash: str,
        hash_algorithm: str,
        object_size: int,
    ) -> StorageObject | None:
        return await self.db.scalar(
            select(StorageObject)
            .where(
                and_(
                    StorageObject.object_hash == object_hash,
                    StorageObject.hash_algorithm == hash_algorithm,
                    StorageObject.object_size == object_size,
                    StorageObject.upload_status == UploadStatus.ACTIVE,
                )
            )
            .order_by(StorageObject.object_id.asc())
            .limit(1)
        )

    async def _create_file_from_storage_object(
        self,
        *,
        user_id: int,
        folder_id: int,
        file_name: str,
        mime_type: str | None,
        storage_object: StorageObject,
    ) -> File:
        same_name = await self._find_conflict_file(user_id=user_id, folder_id=folder_id, file_name=file_name)
        if same_name is not None and same_name.storage_object_id == storage_object.object_id:
            return same_name

        final_name = file_name
        if same_name is not None:
            final_name = await self._next_available_file_name(
                user_id=user_id,
                folder_id=folder_id,
                original_name=file_name,
            )
        resolved_mime_type = resolve_file_mime_type(
            mime_type=mime_type or storage_object.content_type,
            file_ext=self._extract_ext(final_name),
            file_name=final_name,
            default=DEFAULT_MIME_TYPE,
        )

        file_row = File(
            uploader_id=user_id,
            owner_id=user_id,
            folder_id=folder_id,
            file_name=final_name,
            file_ext=self._extract_ext(final_name),
            mime_type=resolved_mime_type,
            storage_object_id=storage_object.object_id,
            file_size=storage_object.object_size,
            status=FileStatus.ACTIVE,
        )
        self.db.add(file_row)
        await self.db.flush()
        return file_row

    async def _resolve_folder_id(self, *, user_id: int, parent_id: str) -> int:
        if parent_id == "root":
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
                folder_name = await self._next_available_root_folder_name(user_id=user_id, base_name="My Files")
                folder = Folder(
                    owner_id=user_id,
                    folder_name=folder_name,
                    parent_folder_id=None,
                    status=FolderStatus.ACTIVE,
                    folder_type=FolderType.ROOT,
                )
                self.db.add(folder)
                await self.db.flush()
            return folder.folder_id

        try:
            folder_id = int(parent_id)
        except ValueError as exc:
            raise ApiError(status_code=400, code=400, message="Invalid parentId") from exc

        folder = await self.db.scalar(
            select(Folder).where(
                and_(
                    Folder.folder_id == folder_id,
                    Folder.owner_id == user_id,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if folder is None:
            raise ApiError(status_code=404, code=404, message="Target folder not found")
        return folder.folder_id

    async def _next_available_root_folder_name(self, *, user_id: int, base_name: str) -> str:
        candidate = base_name
        suffix = 1
        while await self.db.scalar(
            select(Folder.folder_id).where(
                and_(
                    Folder.owner_id == user_id,
                    Folder.parent_folder_id.is_(None),
                    Folder.folder_name == candidate,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        ):
            suffix += 1
            candidate = f"{base_name} ({suffix})"
        return candidate

    async def _list_uploaded_indexes(self, *, task_id: int) -> list[int]:
        return list(
            await self.db.scalars(
                select(UploadTaskPart.part_number)
                .where(
                    and_(
                        UploadTaskPart.task_id == task_id,
                        UploadTaskPart.status == UploadPartStatus.UPLOADED,
                    )
                )
                .order_by(UploadTaskPart.part_number.asc())
            )
        )

    async def _collect_task_cleanup_keys(self, *, task: UploadTask) -> list[str]:
        keys: list[str] = []
        if task.object_key:
            keys.append(task.object_key)
        part_indexes = await self._list_uploaded_indexes(task_id=task.task_id)
        keys.extend(self._build_part_object_key(task=task, chunk_index=index) for index in part_indexes)
        # Preserve order but deduplicate possible repeated entries.
        return list(dict.fromkeys(keys))

    async def _abort_task(self, *, task: UploadTask, reason: str) -> None:
        task.status = UploadTaskStatus.ABORTED
        task.last_error = reason
        await self.db.commit()

    async def _find_conflict_file(self, *, user_id: int, folder_id: int, file_name: str) -> File | None:
        return await self.db.scalar(
            select(File)
            .where(
                and_(
                    File.owner_id == user_id,
                    File.folder_id == folder_id,
                    File.file_name == file_name,
                    File.status == FileStatus.ACTIVE,
                )
            )
            .order_by(File.file_id.asc())
            .limit(1)
        )

    async def _next_available_file_name(self, *, user_id: int, folder_id: int, original_name: str) -> str:
        stem = Path(original_name).stem or "file"
        suffix = Path(original_name).suffix
        index = 1
        while True:
            candidate = f"{stem} ({index}){suffix}"
            conflict = await self._find_conflict_file(user_id=user_id, folder_id=folder_id, file_name=candidate)
            if conflict is None:
                return candidate
            index += 1

    def _build_conflict_data(self, conflict: File) -> dict[str, object]:
        return {
            "type": "file_name_conflict",
            "conflictingFileId": str(conflict.file_id),
            "conflictingFileName": conflict.file_name,
            "availableStrategies": ["rename", "overwrite", "cancel"],
        }

    def _normalize_hash(self, file_hash: str) -> tuple[str, str]:
        value = file_hash.strip().lower()
        if len(value) == 32 and self._is_hex(value):
            return value, "md5"
        if len(value) == 64 and self._is_hex(value):
            return value, "sha256"
        raise ApiError(status_code=400, code=400, message="fileHash must be a valid md5 or sha256 string")

    def _validate_upload_size(self, file_size: int) -> None:
        if file_size <= 0:
            raise ApiError(status_code=400, code=400, message="fileSize must be greater than 0")
        if file_size > self.settings.upload_single_file_size_max:
            raise ApiError(status_code=413, code=413, message="File size exceeds maximum upload limit")

    def _resolved_chunk_size(self) -> int:
        lower = max(1, self.settings.upload_chunk_size_min)
        upper = max(lower, self.settings.upload_chunk_size_max)
        default = self.settings.upload_chunk_size_default
        return min(max(default, lower), upper)

    def _build_object_key(self, *, user_id: int) -> str:
        return f"{self.settings.upload_object_prefix}/u{user_id}/{uuid4().hex}"

    def _build_part_object_key(self, *, task: UploadTask, chunk_index: int) -> str:
        upload_id = task.upload_id or f"task-{task.task_id}"
        return f"{self.settings.upload_temp_prefix}/u{task.user_id}/{upload_id}/part-{chunk_index:08d}"

    @staticmethod
    def _build_merge_job_idempotency_key(
        *,
        user_id: int,
        upload_id: str,
        merge_request_payload: dict[str, Any],
    ) -> str:
        canonical = json.dumps(merge_request_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
        return f"upload:{user_id}:{upload_id}:merge:{digest}"

    @staticmethod
    def _extract_ext(file_name: str) -> str | None:
        suffix = Path(file_name).suffix.strip(".").lower()
        return suffix or None

    @staticmethod
    def _is_hex(value: str) -> bool:
        return all(char in "0123456789abcdef" for char in value)

    @staticmethod
    def _normalize_task_hash(value: str | None) -> str:
        return (value or "").strip().lower()

    async def _enqueue_transcode_after_merge(
        self,
        *,
        user_id: int,
        file_row: File,
        storage_object: StorageObject,
    ) -> None:
        source_object_id = await self._resolve_storage_object_id(
            storage_object=storage_object,
            file_row=file_row,
        )
        if source_object_id is None:
            logger.warning(
                "Skip transcode enqueue because source object id is missing userId=%s fileId=%s objectKey=%s",
                user_id,
                file_row.file_id,
                storage_object.object_key,
            )
            return

        output_key = self._build_transcode_output_key(
            source_object_id=source_object_id,
            source_object_key=storage_object.object_key,
            media_type=self._media_type_from_mime(file_row.mime_type or storage_object.content_type),
        )
        idempotency_key = f"object:{source_object_id}:transcode:{TRANSCODE_PROFILE_VERSION}"
        now = datetime.now(UTC)

        metadata = await self.db.scalar(
            select(FileMediaMetadata).where(FileMediaMetadata.source_object_id == source_object_id).limit(1)
        )
        if metadata is None:
            metadata = FileMediaMetadata(source_object_id=source_object_id)
            self.db.add(metadata)

        extra = dict(metadata.extra_metadata or {})
        extra["transcode"] = {
            "status": "queued",
            "mediaType": self._media_type_from_mime(file_row.mime_type or storage_object.content_type),
            "profileVersion": TRANSCODE_PROFILE_VERSION,
            "optimizedBucketName": self.settings.object_storage_bucket,
            "optimizedObjectKey": output_key,
            "updatedAt": now.isoformat(),
        }
        metadata.extra_metadata = extra
        metadata.extracted_at = now
        await self.db.commit()

        jobs = self.jobs
        if jobs is None:
            failed_extra = dict(metadata.extra_metadata or {})
            failed_extra["transcode"] = {
                "status": "failed",
                "mediaType": self._media_type_from_mime(file_row.mime_type or storage_object.content_type),
                "profileVersion": TRANSCODE_PROFILE_VERSION,
                "optimizedBucketName": self.settings.object_storage_bucket,
                "optimizedObjectKey": output_key,
                "error": "Job queue unavailable",
                "updatedAt": datetime.now(UTC).isoformat(),
            }
            metadata.extra_metadata = failed_extra
            metadata.extracted_at = datetime.now(UTC)
            await self.db.commit()
            return

        try:
            await jobs.enqueue_transcode_job(
                self.db,
                source_bucket_name=storage_object.bucket_name,
                source_object_key=storage_object.object_key,
                source_object_id=source_object_id,
                output_bucket_name=self.settings.object_storage_bucket,
                output_object_key=output_key,
                file_id=int(file_row.file_id),
                requested_by=user_id,
                idempotency_key=idempotency_key,
            )
        except ApiError as exc:
            logger.warning(
                "Enqueue transcode failed but upload kept userId=%s fileId=%s objectId=%s error=%s",
                user_id,
                file_row.file_id,
                storage_object.object_id,
                exc.message,
            )
            failed_extra = dict(metadata.extra_metadata or {})
            failed_extra["transcode"] = {
                "status": "failed",
                "mediaType": self._media_type_from_mime(file_row.mime_type or storage_object.content_type),
                "profileVersion": TRANSCODE_PROFILE_VERSION,
                "optimizedBucketName": self.settings.object_storage_bucket,
                "optimizedObjectKey": output_key,
                "error": exc.message[:500],
                "updatedAt": datetime.now(UTC).isoformat(),
            }
            metadata.extra_metadata = failed_extra
            metadata.extracted_at = datetime.now(UTC)
            await self.db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Unexpected transcode enqueue failure but upload kept userId=%s fileId=%s objectId=%s",
                user_id,
                file_row.file_id,
                storage_object.object_id,
            )
            failed_extra = dict(metadata.extra_metadata or {})
            failed_extra["transcode"] = {
                "status": "failed",
                "mediaType": self._media_type_from_mime(file_row.mime_type or storage_object.content_type),
                "profileVersion": TRANSCODE_PROFILE_VERSION,
                "optimizedBucketName": self.settings.object_storage_bucket,
                "optimizedObjectKey": output_key,
                "error": f"{type(exc).__name__}: {exc}"[:500],
                "updatedAt": datetime.now(UTC).isoformat(),
            }
            metadata.extra_metadata = failed_extra
            metadata.extracted_at = datetime.now(UTC)
            await self.db.commit()

    async def _resolve_storage_object_id(
        self,
        *,
        storage_object: StorageObject,
        file_row: File,
    ) -> int | None:
        resolved = self._coerce_positive_int(storage_object.object_id) or self._coerce_positive_int(file_row.storage_object_id)
        if resolved is not None:
            return resolved

        await self.db.flush()
        resolved = self._coerce_positive_int(storage_object.object_id) or self._coerce_positive_int(file_row.storage_object_id)
        return resolved

    @staticmethod
    def _is_transcode_candidate(mime_type: str | None) -> bool:
        value = (mime_type or "").lower()
        return value.startswith("video/") or value.startswith("audio/")

    @staticmethod
    def _media_type_from_mime(mime_type: str | None) -> str:
        value = (mime_type or "").lower()
        return "video" if value.startswith("video/") else "audio"

    @staticmethod
    def _build_transcode_output_key(*, source_object_id: int, source_object_key: str, media_type: str) -> str:
        suffix = ".mp4" if media_type == "video" else ".m4a"
        original_stem = Path(source_object_key).stem or f"obj-{source_object_id}"
        return (
            f"optimized/transcode/v1/object-{source_object_id}/"
            f"{original_stem}-{TRANSCODE_PROFILE_VERSION}{suffix}"
        )

    @staticmethod
    def _coerce_positive_int(value: object) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None
