from __future__ import annotations

import json
import logging
import mimetypes
import shutil
import tarfile
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from minio import Minio
from minio.error import S3Error

from ..core import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ArchiveLimits:
    preview_max_entries: int
    extract_max_entries: int
    extract_max_total_bytes: int
    extract_max_file_bytes: int


def run_archive_preview(payload: dict[str, Any] | Any) -> dict[str, Any]:
    settings = get_settings()
    limits = _limits_from_settings(settings)

    bucket_name, object_key, file_name = _get_storage_ref(payload)
    archive_format = _detect_archive_format(file_name)
    suffix = _suffix_for_download(file_name)

    local_path = _maybe_local_path(payload)
    download_path: Path | None = None
    try:
        archive_path = local_path or _download_object(
            settings=settings,
            bucket_name=bucket_name,
            object_key=object_key,
            suffix=suffix,
        )
        if local_path is None:
            download_path = archive_path

        entries, summary = _preview_archive(
            archive_path=archive_path,
            archive_format=archive_format,
            max_entries=limits.preview_max_entries,
        )
        return {
            "archive": {"format": archive_format, "fileName": file_name},
            "entries": entries,
            "summary": summary,
            "previewedAt": datetime.now(UTC).isoformat(),
        }
    finally:
        if download_path is not None:
            _safe_unlink(download_path)


def run_archive_extract(payload: dict[str, Any] | Any) -> dict[str, Any]:
    settings = get_settings()
    limits = _limits_from_settings(settings)

    bucket_name, object_key, file_name = _get_storage_ref(payload)
    archive_format = _detect_archive_format(file_name)
    job_id = _coerce_int(payload.get("jobId"))
    requested_by = _coerce_int(payload.get("requestedBy"))
    if job_id is None:
        raise ValueError("Archive extract payload requires jobId")
    if requested_by is None:
        raise ValueError("Archive extract payload requires requestedBy")

    suffix = _suffix_for_download(file_name)
    base_dir = _task_temp_dir()
    extract_dir = base_dir / f"extract-{job_id}-{uuid.uuid4().hex[:10]}"
    extract_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = base_dir / f"manifest-{job_id}-{uuid.uuid4().hex[:10]}.jsonl"

    local_path = _maybe_local_path(payload)
    download_path: Path | None = None
    extracted_files: list[tuple[str, Path]] = []
    extracted_dirs: set[str] = set()
    skipped_entries = 0
    try:
        archive_path = local_path or _download_object(
            settings=settings,
            bucket_name=bucket_name,
            object_key=object_key,
            suffix=suffix,
        )
        if local_path is None:
            download_path = archive_path

        extracted_files, extracted_dirs, skipped_entries = _extract_archive_to_dir(
            archive_path=archive_path,
            archive_format=archive_format,
            extract_dir=extract_dir,
            limits=limits,
        )

        _ensure_bucket(settings, bucket_name=bucket_name)

        total_bytes = 0
        with manifest_path.open("w", encoding="utf-8") as manifest_fp:
            for rel_dir in sorted(extracted_dirs):
                manifest_fp.write(json.dumps({"type": "dir", "path": rel_dir}, ensure_ascii=False) + "\n")

            for rel_path, abs_path in extracted_files:
                file_size = abs_path.stat().st_size
                if file_size > limits.extract_max_file_bytes:
                    raise ValueError(f"Archive member too large: {rel_path} size={file_size}")

                digest = _sha256_file(abs_path)
                content_type = mimetypes.guess_type(rel_path)[0] or "application/octet-stream"
                object_key_for_file = _build_extracted_object_key(
                    settings=settings,
                    requested_by=requested_by,
                    job_id=job_id,
                    rel_path=rel_path,
                )

                etag, version_id = _upload_file_to_object_storage(
                    settings=settings,
                    bucket_name=bucket_name,
                    object_key=object_key_for_file,
                    file_path=abs_path,
                    content_type=content_type,
                )

                total_bytes += file_size
                manifest_fp.write(
                    json.dumps(
                        {
                            "type": "file",
                            "path": rel_path,
                            "bucketName": bucket_name,
                            "objectKey": object_key_for_file,
                            "size": file_size,
                            "sha256": digest,
                            "hashAlgorithm": "sha256",
                            "etag": etag,
                            "versionId": version_id,
                            "contentType": content_type,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

        return {
            "archive": {"format": archive_format, "fileName": file_name},
            "summary": {
                "extractedFiles": len(extracted_files),
                "extractedDirs": len(extracted_dirs),
                "skippedEntries": skipped_entries,
                "totalBytes": total_bytes,
            },
            "manifestPath": str(manifest_path),
            "extractedAt": datetime.now(UTC).isoformat(),
        }
    finally:
        if download_path is not None:
            _safe_unlink(download_path)
        shutil.rmtree(extract_dir, ignore_errors=True)


def _limits_from_settings(settings: Settings) -> ArchiveLimits:
    return ArchiveLimits(
        preview_max_entries=max(1, int(getattr(settings, "archive_preview_max_entries", 2000))),
        extract_max_entries=max(1, int(getattr(settings, "archive_extract_max_entries", 20000))),
        extract_max_total_bytes=max(1, int(getattr(settings, "archive_extract_max_total_bytes", 10 * 1024**3))),
        extract_max_file_bytes=max(1, int(getattr(settings, "archive_extract_max_file_bytes", 2 * 1024**3))),
    )


def _maybe_local_path(payload: dict[str, Any] | Any) -> Path | None:
    raw = str(payload.get("localPath") or payload.get("inputPath") or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Archive localPath not found: {path}")
    return path


def _task_temp_dir() -> Path:
    base = Path(tempfile.gettempdir()) / "fileflash" / "archive"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _suffix_for_download(file_name: str) -> str:
    lower = file_name.strip().lower()
    if lower.endswith(".tar.gz"):
        return ".tar.gz"
    if lower.endswith(".tgz"):
        return ".tgz"
    return Path(lower).suffix or ".bin"


def _get_storage_ref(payload: dict[str, Any] | Any) -> tuple[str, str, str]:
    bucket_name = str(payload.get("bucketName") or payload.get("bucket_name") or "").strip()
    object_key = str(payload.get("objectKey") or payload.get("object_key") or "").strip()
    file_name = str(payload.get("fileName") or payload.get("file_name") or "").strip()
    if not bucket_name:
        raise ValueError("Archive payload requires bucketName")
    if not object_key:
        raise ValueError("Archive payload requires objectKey")
    if not file_name:
        raise ValueError("Archive payload requires fileName")
    return bucket_name, object_key, file_name


def _detect_archive_format(file_name: str) -> str:
    lower = file_name.strip().lower()
    if lower.endswith(".zip"):
        return "zip"
    if lower.endswith(".7z"):
        return "7z"
    if lower.endswith(".tar.gz") or lower.endswith(".tgz") or lower.endswith(".gz"):
        return "tar.gz"
    if lower.endswith(".tar"):
        return "tar"
    return "unknown"


def _preview_archive(
    *,
    archive_path: Path,
    archive_format: str,
    max_entries: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if archive_format == "zip":
        return _preview_zip(archive_path=archive_path, max_entries=max_entries)
    if archive_format in ("tar", "tar.gz"):
        return _preview_tar(archive_path=archive_path, max_entries=max_entries)
    if archive_format == "7z":
        return _preview_7z(archive_path=archive_path, max_entries=max_entries)
    raise ValueError("Unsupported archive format")


def _preview_zip(*, archive_path: Path, max_entries: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with zipfile.ZipFile(archive_path, "r") as zf:
        infos = zf.infolist()
        if any(info.flag_bits & 0x1 for info in infos):
            raise ValueError("Encrypted ZIP is not supported")

        file_infos = [info for info in infos if not info.is_dir()]
        total_entries = len(infos)
        total_uncompressed = sum(int(info.file_size or 0) for info in file_infos)
        entries: list[dict[str, Any]] = []
        for info in infos[:max_entries]:
            normalized = _sanitize_archive_member_path(info.filename, is_dir=info.is_dir())
            if normalized is None:
                continue
            entries.append(
                {
                    "path": normalized,
                    "isDir": bool(info.is_dir()),
                    "size": int(info.file_size or 0),
                    "compressedSize": int(info.compress_size or 0),
                }
            )

        summary = {
            "totalEntries": total_entries,
            "fileCount": len(file_infos),
            "dirCount": total_entries - len(file_infos),
            "totalUncompressedBytes": total_uncompressed,
            "truncated": total_entries > max_entries,
        }
        return entries, summary


def _preview_tar(*, archive_path: Path, max_entries: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with tarfile.open(archive_path, "r:*") as tf:
        members = tf.getmembers()
        file_members = [member for member in members if member.isfile()]
        total_entries = len(members)
        total_uncompressed = sum(int(member.size or 0) for member in file_members)

        entries: list[dict[str, Any]] = []
        for member in members[:max_entries]:
            if member.issym() or member.islnk():
                continue
            normalized = _sanitize_archive_member_path(member.name, is_dir=member.isdir())
            if normalized is None:
                continue
            entries.append(
                {
                    "path": normalized,
                    "isDir": bool(member.isdir()),
                    "size": int(member.size or 0) if member.isfile() else 0,
                }
            )

        summary = {
            "totalEntries": total_entries,
            "fileCount": len(file_members),
            "dirCount": sum(1 for member in members if member.isdir()),
            "totalUncompressedBytes": total_uncompressed,
            "truncated": total_entries > max_entries,
        }
        return entries, summary


def _preview_7z(*, archive_path: Path, max_entries: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        import py7zr  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ValueError("7z support is not installed") from exc

    with py7zr.SevenZipFile(archive_path, mode="r") as archive:
        try:
            file_infos = archive.list()
        except Exception:  # pragma: no cover
            file_infos = []

        entries: list[dict[str, Any]] = []
        total_entries = 0
        file_count = 0
        dir_count = 0
        total_uncompressed = 0

        if file_infos:
            total_entries = len(file_infos)
            for info in file_infos:
                name = getattr(info, "filename", None) or getattr(info, "name", None)
                if not name:
                    continue
                is_dir = bool(getattr(info, "is_directory", False))
                size = int(getattr(info, "uncompressed", 0) or 0)
                if is_dir:
                    dir_count += 1
                else:
                    file_count += 1
                    total_uncompressed += size

                if len(entries) < max_entries:
                    normalized = _sanitize_archive_member_path(str(name), is_dir=is_dir)
                    if normalized is None:
                        continue
                    entries.append({"path": normalized, "isDir": is_dir, "size": size})
        else:
            names = list(archive.getnames() or [])
            total_entries = len(names)
            for name in names[:max_entries]:
                normalized = _sanitize_archive_member_path(str(name), is_dir=False)
                if normalized is None:
                    continue
                entries.append({"path": normalized, "isDir": False, "size": 0})

        summary = {
            "totalEntries": total_entries,
            "fileCount": file_count,
            "dirCount": dir_count,
            "totalUncompressedBytes": total_uncompressed,
            "truncated": total_entries > max_entries,
        }
        return entries, summary


def _extract_archive_to_dir(
    *,
    archive_path: Path,
    archive_format: str,
    extract_dir: Path,
    limits: ArchiveLimits,
) -> tuple[list[tuple[str, Path]], set[str], int]:
    if archive_format == "zip":
        return _extract_zip(archive_path=archive_path, extract_dir=extract_dir, limits=limits)
    if archive_format in ("tar", "tar.gz"):
        return _extract_tar(archive_path=archive_path, extract_dir=extract_dir, limits=limits)
    if archive_format == "7z":
        return _extract_7z(archive_path=archive_path, extract_dir=extract_dir, limits=limits)
    raise ValueError("Unsupported archive format")


def _extract_zip(
    *,
    archive_path: Path,
    extract_dir: Path,
    limits: ArchiveLimits,
) -> tuple[list[tuple[str, Path]], set[str], int]:
    skipped = 0
    extracted_dirs: set[str] = set()
    extracted_files: list[tuple[str, Path]] = []

    with zipfile.ZipFile(archive_path, "r") as zf:
        infos = zf.infolist()
        if any(info.flag_bits & 0x1 for info in infos):
            raise ValueError("Encrypted ZIP is not supported")

        if len(infos) > limits.extract_max_entries:
            raise ValueError(f"Archive contains too many entries: {len(infos)}")

        total_uncompressed = sum(int(info.file_size or 0) for info in infos if not info.is_dir())
        if total_uncompressed > limits.extract_max_total_bytes:
            raise ValueError(f"Archive is too large to extract: {total_uncompressed} bytes")

        for info in infos:
            rel = _sanitize_archive_member_path(info.filename, is_dir=info.is_dir())
            if rel is None:
                skipped += 1
                continue

            rel_path = PurePosixPath(rel)
            if info.is_dir():
                extracted_dirs.add(str(rel_path))
                (extract_dir / Path(*rel_path.parts)).mkdir(parents=True, exist_ok=True)
                continue

            if int(info.file_size or 0) > limits.extract_max_file_bytes:
                raise ValueError(f"Archive member too large: {rel} size={info.file_size}")

            dst = extract_dir / Path(*rel_path.parts)
            dst.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, "r") as src, dst.open("wb") as out:
                shutil.copyfileobj(src, out, length=1024 * 1024)
            extracted_files.append((str(rel_path), dst))

            if rel_path.parent and str(rel_path.parent) != ".":
                extracted_dirs.add(str(rel_path.parent))

    return extracted_files, extracted_dirs, skipped


def _extract_tar(
    *,
    archive_path: Path,
    extract_dir: Path,
    limits: ArchiveLimits,
) -> tuple[list[tuple[str, Path]], set[str], int]:
    skipped = 0
    extracted_dirs: set[str] = set()
    extracted_files: list[tuple[str, Path]] = []

    with tarfile.open(archive_path, "r:*") as tf:
        members = tf.getmembers()
        if len(members) > limits.extract_max_entries:
            raise ValueError(f"Archive contains too many entries: {len(members)}")

        total_uncompressed = sum(int(m.size or 0) for m in members if m.isfile())
        if total_uncompressed > limits.extract_max_total_bytes:
            raise ValueError(f"Archive is too large to extract: {total_uncompressed} bytes")

        for member in members:
            if member.issym() or member.islnk():
                skipped += 1
                continue
            if not (member.isdir() or member.isfile()):
                skipped += 1
                continue

            rel = _sanitize_archive_member_path(member.name, is_dir=member.isdir())
            if rel is None:
                skipped += 1
                continue

            rel_path = PurePosixPath(rel)
            dst = extract_dir / Path(*rel_path.parts)

            if member.isdir():
                extracted_dirs.add(str(rel_path))
                dst.mkdir(parents=True, exist_ok=True)
                continue

            if int(member.size or 0) > limits.extract_max_file_bytes:
                raise ValueError(f"Archive member too large: {rel} size={member.size}")

            dst.parent.mkdir(parents=True, exist_ok=True)
            src = tf.extractfile(member)
            if src is None:
                skipped += 1
                continue
            with src, dst.open("wb") as out:
                shutil.copyfileobj(src, out, length=1024 * 1024)
            extracted_files.append((str(rel_path), dst))

            if rel_path.parent and str(rel_path.parent) != ".":
                extracted_dirs.add(str(rel_path.parent))

    return extracted_files, extracted_dirs, skipped


def _extract_7z(
    *,
    archive_path: Path,
    extract_dir: Path,
    limits: ArchiveLimits,
) -> tuple[list[tuple[str, Path]], set[str], int]:
    try:
        import py7zr  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ValueError("7z support is not installed") from exc

    with py7zr.SevenZipFile(archive_path, mode="r") as archive:
        file_infos = list(archive.list() or [])
        if file_infos and len(file_infos) > limits.extract_max_entries:
            raise ValueError(f"Archive contains too many entries: {len(file_infos)}")

        total_uncompressed = 0
        for info in file_infos:
            if getattr(info, "is_symlink", False) or getattr(info, "is_junction", False):
                raise ValueError("7z archive contains unsupported link entry")
            is_dir = bool(getattr(info, "is_directory", False))
            if not is_dir:
                total_uncompressed += int(getattr(info, "uncompressed", 0) or 0)
        if total_uncompressed > limits.extract_max_total_bytes:
            raise ValueError(f"Archive is too large to extract: {total_uncompressed} bytes")

        names = list(archive.getnames() or [])
        for name in names:
            if _sanitize_archive_member_path(name, is_dir=False) is None:
                raise ValueError("7z archive contains unsafe member path")

        try:
            archive.extractall(path=extract_dir)
        except Exception as exc:
            raise ValueError(f"Failed to extract 7z archive: {exc}") from exc

    extracted_files: list[tuple[str, Path]] = []
    extracted_dirs: set[str] = set()
    for abs_path in extract_dir.rglob("*"):
        if abs_path.is_dir():
            rel = abs_path.relative_to(extract_dir).as_posix()
            if rel and rel != ".":
                extracted_dirs.add(rel)
            continue
        rel = abs_path.relative_to(extract_dir).as_posix()
        if rel and rel != ".":
            extracted_files.append((rel, abs_path))
            parent = str(PurePosixPath(rel).parent)
            if parent and parent != ".":
                extracted_dirs.add(parent)

    return extracted_files, extracted_dirs, 0


def _sanitize_archive_member_path(raw: str, *, is_dir: bool) -> str | None:
    if raw is None:
        return None
    text = str(raw).replace("\\", "/").strip()
    if not text:
        return None
    if "\x00" in text:
        return None
    if text.startswith("/"):
        return None
    if len(text) >= 2 and text[1] == ":":
        return None
    if is_dir and text.endswith("/"):
        text = text[:-1]

    try:
        posix = PurePosixPath(text)
    except Exception:
        return None

    parts = [part for part in posix.parts if part not in ("", ".")]
    if not parts:
        return None
    if any(part == ".." for part in parts):
        return None
    if any(len(part) > 255 for part in parts):
        return None
    return PurePosixPath(*parts).as_posix()


def _coerce_int(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _build_extracted_object_key(*, settings: Settings, requested_by: int, job_id: int, rel_path: str) -> str:
    normalized = PurePosixPath(rel_path).as_posix()
    key_hash = sha256(normalized.encode("utf-8")).hexdigest()
    leaf = PurePosixPath(normalized).name
    safe_leaf = "".join(ch for ch in leaf if ch.isalnum() or ch in ("-", "_", "."))
    safe_leaf = (safe_leaf or "file")[:80]
    prefix = getattr(settings, "upload_object_prefix", "objects")
    return f"{prefix}/u{requested_by}/archives/j{job_id}/{key_hash}-{safe_leaf}"


def _sha256_file(file_path: Path) -> str:
    hasher = sha256()
    with file_path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _build_minio_client(settings: Settings) -> Minio:
    return Minio(
        endpoint=settings.object_storage_endpoint,
        access_key=settings.object_storage_access_key,
        secret_key=settings.object_storage_secret_key,
        secure=settings.object_storage_secure,
        region=settings.object_storage_region,
    )


def _ensure_bucket(settings: Settings, *, bucket_name: str) -> None:
    client = _build_minio_client(settings)
    try:
        if client.bucket_exists(bucket_name):
            return
        client.make_bucket(bucket_name, location=settings.object_storage_region)
    except S3Error as exc:
        if exc.code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise


def _download_object(*, settings: Settings, bucket_name: str, object_key: str, suffix: str) -> Path:
    client = _build_minio_client(settings)
    _ensure_bucket(settings, bucket_name=bucket_name)

    dest = _task_temp_dir() / f"download-{uuid.uuid4().hex[:12]}{suffix}"
    response = client.get_object(bucket_name, object_key)
    try:
        with dest.open("wb") as fp:
            for chunk in response.stream(1024 * 1024):
                fp.write(chunk)
    finally:
        response.close()
        response.release_conn()

    if not dest.exists() or dest.stat().st_size <= 0:
        raise RuntimeError("Downloaded archive is empty")
    return dest


def _upload_file_to_object_storage(
    *,
    settings: Settings,
    bucket_name: str,
    object_key: str,
    file_path: Path,
    content_type: str,
) -> tuple[str | None, str | None]:
    client = _build_minio_client(settings)
    with file_path.open("rb") as fp:
        result = client.put_object(
            bucket_name,
            object_key,
            fp,
            length=file_path.stat().st_size,
            content_type=content_type,
        )
    return getattr(result, "etag", None), getattr(result, "version_id", None)


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        logger.debug("Failed to remove temp file: %s", path, exc_info=True)

