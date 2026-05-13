from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.transaction import is_unique_violation_error
from ..models import File, FileMediaMetadata, Folder, ObjectScanResult, StorageObject
from ..models.enums import FileStatus, FolderStatus, FolderType, ScanResult


async def apply_task_effects(
    db: AsyncSession,
    *,
    task_type: str,
    payload: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    if task_type in ("task.scan", "scan.dangerous_file"):
        await _apply_scan_effects(db, payload=payload, result=result)
        return {}
    if task_type in ("task.transcode", "media.transcode"):
        await _apply_transcode_effects(db, payload=payload, result=result)
        return {}
    if task_type in ("task.archive_extract", "archive.extract"):
        return await _apply_archive_extract_effects(db, payload=payload, result=result)
    return {}


async def _apply_scan_effects(
    db: AsyncSession,
    *,
    payload: dict[str, Any],
    result: dict[str, Any],
) -> None:
    object_id = _coerce_int(payload.get("objectId"))
    if object_id is None:
        return

    scan_result = _map_scan_result(result.get("scanResult"))
    now = datetime.now(UTC)

    storage = await db.get(StorageObject, object_id)
    if storage is not None:
        storage.scan_status = scan_result
        storage.last_scanned_at = now
        if scan_result in (ScanResult.BLOCKED, ScanResult.INFECTED):
            storage.quarantined_at = now

    db.add(
        ObjectScanResult(
            object_id=object_id,
            scan_type=str(result.get("scanType") or "dangerousFileHeuristic"),
            engine_name=_truncate(result.get("engineName"), 100),
            engine_version=_truncate(result.get("engineVersion"), 100),
            result=scan_result,
            details=result.get("details") or {},
            scanned_at=now,
        )
    )


async def _apply_transcode_effects(
    db: AsyncSession,
    *,
    payload: dict[str, Any],
    result: dict[str, Any],
) -> None:
    object_id = _coerce_int(payload.get("sourceObjectId")) or _coerce_int(payload.get("objectId"))
    if object_id is None:
        return

    metadata = result.get("metadata") or {}
    now = datetime.now(UTC)
    row = await db.scalar(
        select(FileMediaMetadata).where(FileMediaMetadata.source_object_id == object_id).limit(1)
    )
    if row is None:
        row = FileMediaMetadata(source_object_id=object_id)
        db.add(row)

    row.width = _coerce_int(metadata.get("width"))
    row.height = _coerce_int(metadata.get("height"))
    row.duration_ms = _coerce_int(metadata.get("durationMs"))
    row.bitrate = _coerce_int(metadata.get("bitrate"))
    row.sample_rate = _coerce_int(metadata.get("sampleRate"))
    row.video_codec = _truncate(metadata.get("videoCodec"), 64)
    row.audio_codec = _truncate(metadata.get("audioCodec"), 64)
    extra = dict(row.extra_metadata or {})
    extra["transcodeProfile"] = result.get("transcodeProfile") or {}
    extra["transcode"] = {
        "status": "ready",
        "mediaType": result.get("mediaType"),
        "profileVersion": (result.get("transcodeProfile") or {}).get("version"),
        "optimizedMimeType": result.get("optimizedMimeType"),
        "optimizedBucketName": result.get("outputBucketName"),
        "optimizedObjectKey": result.get("outputObjectKey"),
        "outputObjectEtag": result.get("outputObjectEtag"),
        "outputObjectVersionId": result.get("outputObjectVersionId"),
        "outputObjectSize": _coerce_int(result.get("outputObjectSize")),
        "updatedAt": now.isoformat(),
    }
    row.extra_metadata = extra
    row.extracted_at = now


async def mark_transcode_running(
    db: AsyncSession,
    *,
    payload: dict[str, Any],
) -> None:
    object_id = _coerce_int(payload.get("sourceObjectId")) or _coerce_int(payload.get("objectId"))
    if object_id is None:
        return

    row = await db.scalar(
        select(FileMediaMetadata).where(FileMediaMetadata.source_object_id == object_id).limit(1)
    )
    if row is None:
        row = FileMediaMetadata(source_object_id=object_id)
        db.add(row)

    now = datetime.now(UTC)
    extra = dict(row.extra_metadata or {})
    transcode = dict(extra.get("transcode") or {})
    transcode["status"] = "running"
    transcode["mediaType"] = transcode.get("mediaType") or payload.get("mediaType")
    transcode["updatedAt"] = now.isoformat()
    if payload.get("outputBucketName"):
        transcode["optimizedBucketName"] = payload.get("outputBucketName")
    if payload.get("outputObjectKey"):
        transcode["optimizedObjectKey"] = payload.get("outputObjectKey")
    if payload.get("profileVersion"):
        transcode["profileVersion"] = payload.get("profileVersion")
    extra["transcode"] = transcode
    row.extra_metadata = extra
    row.extracted_at = now


async def mark_transcode_failed(
    db: AsyncSession,
    *,
    payload: dict[str, Any],
    error_message: str,
) -> None:
    object_id = _coerce_int(payload.get("sourceObjectId")) or _coerce_int(payload.get("objectId"))
    if object_id is None:
        return

    row = await db.scalar(
        select(FileMediaMetadata).where(FileMediaMetadata.source_object_id == object_id).limit(1)
    )
    if row is None:
        row = FileMediaMetadata(source_object_id=object_id)
        db.add(row)

    now = datetime.now(UTC)
    extra = dict(row.extra_metadata or {})
    transcode = dict(extra.get("transcode") or {})
    transcode["status"] = "failed"
    transcode["mediaType"] = transcode.get("mediaType") or payload.get("mediaType")
    transcode["error"] = _truncate(error_message, 500)
    transcode["updatedAt"] = now.isoformat()
    if payload.get("outputBucketName"):
        transcode["optimizedBucketName"] = payload.get("outputBucketName")
    if payload.get("outputObjectKey"):
        transcode["optimizedObjectKey"] = payload.get("outputObjectKey")
    if payload.get("profileVersion"):
        transcode["profileVersion"] = payload.get("profileVersion")
    extra["transcode"] = transcode
    row.extra_metadata = extra
    row.extracted_at = now


async def _apply_archive_extract_effects(
    db: AsyncSession,
    *,
    payload: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    manifest_path = str(result.get("manifestPath") or "").strip()
    if not manifest_path:
        return {}

    requested_by = _coerce_int(payload.get("requestedBy"))
    if requested_by is None:
        return {}

    target_folder_raw = str(payload.get("targetFolderId") or "").strip()
    if not target_folder_raw:
        raise ValueError("Archive extract payload requires targetFolderId")

    conflict_strategy = str(payload.get("conflictStrategy") or "rename").strip().lower()
    if conflict_strategy not in {"rename", "overwrite", "skip"}:
        raise ValueError("conflictStrategy must be rename, overwrite, or skip")

    create_subfolder = bool(payload.get("createSubfolder", True))
    archive_file_name = str(payload.get("fileName") or "").strip()
    subfolder_name = str(payload.get("subfolderName") or "").strip() or _default_subfolder_name(archive_file_name)

    target_folder_id = await _resolve_folder_id(db, user_id=requested_by, folder_id=target_folder_raw)

    extracted_root_id = target_folder_id
    extracted_root_name: str | None = None
    if create_subfolder:
        folder_row = await _create_unique_child_folder(
            db,
            user_id=requested_by,
            parent_folder_id=target_folder_id,
            desired_name=subfolder_name,
        )
        extracted_root_id = int(folder_row.folder_id)
        extracted_root_name = folder_row.folder_name

    folder_cache: dict[tuple[int, str], int] = {}

    inserted_files = 0
    inserted_dirs = 0
    skipped_entries = 0

    manifest = Path(manifest_path)
    if not manifest.exists() or not manifest.is_file():
        raise FileNotFoundError("Archive extract manifest not found")

    lines = manifest.read_text(encoding="utf-8").splitlines()
    entries = [_safe_json_load(line) for line in lines if line.strip()]

    for entry in entries:
        if not entry or entry.get("type") != "dir":
            continue
        rel_dir = str(entry.get("path") or "").strip()
        if not rel_dir:
            continue
        await _ensure_folder_path(
            db,
            user_id=requested_by,
            root_folder_id=extracted_root_id,
            rel_path=rel_dir,
            cache=folder_cache,
        )
        inserted_dirs += 1

    for entry in entries:
        if not entry or entry.get("type") != "file":
            continue
        rel_file = str(entry.get("path") or "").strip()
        if not rel_file:
            skipped_entries += 1
            continue

        rel_posix = PurePosixPath(rel_file)
        file_name = rel_posix.name
        if not file_name:
            skipped_entries += 1
            continue
        parent_rel = str(rel_posix.parent) if str(rel_posix.parent) != "." else ""
        parent_folder_id = extracted_root_id
        if parent_rel:
            parent_folder_id = await _ensure_folder_path(
                db,
                user_id=requested_by,
                root_folder_id=extracted_root_id,
                rel_path=parent_rel,
                cache=folder_cache,
            )

        existing = await db.scalar(
            select(File)
            .where(
                and_(
                    File.owner_id == requested_by,
                    File.folder_id == parent_folder_id,
                    File.file_name == file_name,
                    File.status == FileStatus.ACTIVE,
                )
            )
            .limit(1)
        )
        if existing is not None:
            if conflict_strategy == "skip":
                skipped_entries += 1
                continue
            if conflict_strategy == "overwrite":
                existing.status = FileStatus.DELETED
                existing.deleted_at = datetime.now(UTC)
                existing.deleted_by = requested_by
            else:
                file_name = await _next_available_file_name(
                    db,
                    user_id=requested_by,
                    folder_id=parent_folder_id,
                    original_name=file_name,
                )

        bucket_name = str(entry.get("bucketName") or "").strip()
        object_key = str(entry.get("objectKey") or "").strip()
        file_size = _coerce_int(entry.get("size")) or 0
        object_hash = str(entry.get("sha256") or "").strip() or None
        hash_algorithm = str(entry.get("hashAlgorithm") or "sha256").strip().lower() or "sha256"
        content_type = str(entry.get("contentType") or "").strip() or None
        etag = str(entry.get("etag") or "").strip() or None
        version_id = str(entry.get("versionId") or "").strip() or None

        if not bucket_name or not object_key:
            skipped_entries += 1
            continue

        storage = await db.scalar(
            select(StorageObject)
            .where(
                and_(
                    StorageObject.bucket_name == bucket_name,
                    StorageObject.object_key == object_key,
                )
            )
            .limit(1)
        )
        if storage is None:
            storage = await _get_or_create_storage_object(
                db,
                bucket_name=bucket_name,
                object_key=object_key,
                object_size=file_size,
                object_hash=object_hash,
                hash_algorithm=hash_algorithm,
                etag=etag,
                version_id=version_id,
                content_type=content_type,
            )

        inserted = await _insert_file_with_conflict_retry(
            db,
            user_id=requested_by,
            folder_id=parent_folder_id,
            file_name=file_name,
            content_type=content_type,
            storage_object_id=int(storage.object_id),
            file_size=file_size,
            conflict_strategy=conflict_strategy,
        )
        if inserted:
            inserted_files += 1
        else:
            skipped_entries += 1

    try:
        manifest.unlink(missing_ok=True)
    except Exception:
        pass

    extra: dict[str, Any] = {
        "summary": {
            "extractedFiles": inserted_files,
            "extractedDirs": inserted_dirs,
            "skippedEntries": skipped_entries,
        }
    }
    if create_subfolder:
        extra["extractedFolderId"] = str(extracted_root_id)
        extra["extractedFolderName"] = extracted_root_name
    return extra


def _map_scan_result(raw: Any) -> ScanResult:
    if isinstance(raw, ScanResult):
        return raw
    if raw is None:
        return ScanResult.FAILED
    text = str(raw).strip().lower()
    mapping = {
        "pending": ScanResult.PENDING,
        "clean": ScanResult.CLEAN,
        "infected": ScanResult.INFECTED,
        "blocked": ScanResult.BLOCKED,
        "failed": ScanResult.FAILED,
    }
    return mapping.get(text, ScanResult.FAILED)


def _coerce_int(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _truncate(raw: Any, max_len: int) -> str | None:
    if raw is None:
        return None
    text = str(raw)
    return text[:max_len]


def _safe_json_load(line: str) -> dict[str, Any] | None:
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        return None
    if isinstance(value, dict):
        return value
    return None


async def _resolve_folder_id(db: AsyncSession, *, user_id: int, folder_id: str) -> int:
    if folder_id == "root":
        folder = await db.scalar(
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
            folder_name = await _next_available_root_folder_name(db, user_id=user_id, base_name="My Files")
            folder = Folder(
                owner_id=user_id,
                folder_name=folder_name,
                parent_folder_id=None,
                status=FolderStatus.ACTIVE,
                folder_type=FolderType.ROOT,
            )
            db.add(folder)
            await db.flush()
        return int(folder.folder_id)

    try:
        parsed = int(folder_id)
    except ValueError as exc:
        raise ValueError("Invalid targetFolderId") from exc

    folder = await db.scalar(
        select(Folder).where(
            and_(
                Folder.folder_id == parsed,
                Folder.owner_id == user_id,
                Folder.status == FolderStatus.ACTIVE,
            )
        )
    )
    if folder is None:
        raise FileNotFoundError("Target folder not found")
    return int(folder.folder_id)


async def _next_available_root_folder_name(db: AsyncSession, *, user_id: int, base_name: str) -> str:
    candidate = base_name
    suffix = 1
    while await db.scalar(
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


async def _create_unique_child_folder(
    db: AsyncSession,
    *,
    user_id: int,
    parent_folder_id: int,
    desired_name: str,
) -> Folder:
    name = (desired_name or "Extracted").strip()[:255]
    candidate = name or "Extracted"
    suffix = 1
    while True:
        while await db.scalar(
            select(Folder.folder_id).where(
                and_(
                    Folder.owner_id == user_id,
                    Folder.parent_folder_id == parent_folder_id,
                    Folder.folder_name == candidate,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        ):
            suffix += 1
            candidate = f"{name} ({suffix})"

        folder = Folder(
            owner_id=user_id,
            folder_name=candidate,
            parent_folder_id=parent_folder_id,
            status=FolderStatus.ACTIVE,
            folder_type=FolderType.NORMAL,
        )
        try:
            await _flush_with_optional_savepoint(db, folder)
            return folder
        except IntegrityError as exc:
            if not is_unique_violation_error(exc):
                raise
            suffix += 1
            candidate = f"{name} ({suffix})"


async def _ensure_folder_path(
    db: AsyncSession,
    *,
    user_id: int,
    root_folder_id: int,
    rel_path: str,
    cache: dict[tuple[int, str], int],
) -> int:
    posix = PurePosixPath(rel_path)
    current_id = root_folder_id
    for part in posix.parts:
        key = (current_id, part)
        cached = cache.get(key)
        if cached is not None:
            current_id = cached
            continue

        existing = await db.scalar(
            select(Folder).where(
                and_(
                    Folder.owner_id == user_id,
                    Folder.parent_folder_id == current_id,
                    Folder.folder_name == part,
                    Folder.status == FolderStatus.ACTIVE,
                )
            )
        )
        if existing is None:
            existing = Folder(
                owner_id=user_id,
                parent_folder_id=current_id,
                folder_name=part[:255],
                status=FolderStatus.ACTIVE,
                folder_type=FolderType.NORMAL,
            )
            try:
                await _flush_with_optional_savepoint(db, existing)
            except IntegrityError as exc:
                if not is_unique_violation_error(exc):
                    raise
                existing = await db.scalar(
                    select(Folder).where(
                        and_(
                            Folder.owner_id == user_id,
                            Folder.parent_folder_id == current_id,
                            Folder.folder_name == part,
                            Folder.status == FolderStatus.ACTIVE,
                        )
                    )
                )
                if existing is None:
                    raise

        current_id = int(existing.folder_id)
        cache[key] = current_id

    return current_id


async def _flush_with_optional_savepoint(db: AsyncSession, entity: Any) -> None:
    begin_nested = getattr(db, "begin_nested", None)
    if callable(begin_nested):
        async with begin_nested():
            db.add(entity)
            await db.flush()
        return

    db.add(entity)
    await db.flush()


async def _get_or_create_storage_object(
    db: AsyncSession,
    *,
    bucket_name: str,
    object_key: str,
    object_size: int,
    object_hash: str | None,
    hash_algorithm: str,
    etag: str | None,
    version_id: str | None,
    content_type: str | None,
) -> StorageObject:
    while True:
        created = StorageObject(
            bucket_name=bucket_name,
            object_key=object_key,
            object_size=object_size,
            object_hash=object_hash,
            hash_algorithm=hash_algorithm,
            etag=etag,
            version_id=version_id,
            content_type=content_type,
        )
        try:
            await _flush_with_optional_savepoint(db, created)
            return created
        except IntegrityError as exc:
            if not is_unique_violation_error(exc):
                raise
            existing = await db.scalar(
                select(StorageObject)
                .where(
                    and_(
                        StorageObject.bucket_name == bucket_name,
                        StorageObject.object_key == object_key,
                    )
                )
                .limit(1)
            )
            if existing is not None:
                return existing


async def _insert_file_with_conflict_retry(
    db: AsyncSession,
    *,
    user_id: int,
    folder_id: int,
    file_name: str,
    content_type: str | None,
    storage_object_id: int,
    file_size: int,
    conflict_strategy: str,
) -> File | None:
    candidate = file_name
    while True:
        row = File(
            uploader_id=user_id,
            owner_id=user_id,
            folder_id=folder_id,
            file_name=candidate,
            file_ext=_extract_ext(candidate),
            mime_type=content_type,
            storage_object_id=storage_object_id,
            file_size=file_size,
            status=FileStatus.ACTIVE,
        )
        try:
            await _flush_with_optional_savepoint(db, row)
            return row
        except IntegrityError as exc:
            if not is_unique_violation_error(exc):
                raise

            existing = await db.scalar(
                select(File)
                .where(
                    and_(
                        File.owner_id == user_id,
                        File.folder_id == folder_id,
                        File.file_name == candidate,
                        File.status == FileStatus.ACTIVE,
                    )
                )
                .limit(1)
            )
            if conflict_strategy == "skip":
                return None
            if conflict_strategy == "overwrite":
                if existing is None:
                    continue
                existing.status = FileStatus.DELETED
                existing.deleted_at = datetime.now(UTC)
                existing.deleted_by = user_id
                continue

            candidate = await _next_available_file_name(
                db,
                user_id=user_id,
                folder_id=folder_id,
                original_name=candidate,
            )


async def _next_available_file_name(
    db: AsyncSession,
    *,
    user_id: int,
    folder_id: int,
    original_name: str,
) -> str:
    stem = Path(original_name).stem or "file"
    suffix = Path(original_name).suffix
    index = 1
    while True:
        candidate = f"{stem} ({index}){suffix}"
        conflict = await db.scalar(
            select(File.file_id).where(
                and_(
                    File.owner_id == user_id,
                    File.folder_id == folder_id,
                    File.file_name == candidate,
                    File.status == FileStatus.ACTIVE,
                )
            )
        )
        if conflict is None:
            return candidate
        index += 1


def _extract_ext(file_name: str) -> str | None:
    suffix = Path(file_name).suffix.strip(".").lower()
    return suffix or None


def _default_subfolder_name(file_name: str) -> str:
    if not file_name:
        return "Extracted"
    lower = file_name.strip().lower()
    if lower.endswith(".tar.gz"):
        base = file_name[: -len(".tar.gz")]
    elif lower.endswith(".tgz"):
        base = file_name[: -len(".tgz")]
    else:
        base = Path(file_name).stem
    base = base.strip() or "Extracted"
    return base[:255]
