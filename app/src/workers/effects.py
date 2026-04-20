from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import FileMediaMetadata, ObjectScanResult, StorageObject
from ..models.enums import ScanResult


async def apply_task_effects(
    db: AsyncSession,
    *,
    task_type: str,
    payload: dict[str, Any],
    result: dict[str, Any],
) -> None:
    if task_type in ("task.scan", "scan.dangerous_file"):
        await _apply_scan_effects(db, payload=payload, result=result)
        return
    if task_type in ("task.transcode", "media.transcode"):
        await _apply_transcode_effects(db, payload=payload, result=result)


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
    object_id = _coerce_int(payload.get("objectId"))
    if object_id is None:
        return

    metadata = result.get("metadata") or {}
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
    row.extra_metadata = {
        "mediaType": result.get("mediaType"),
        "inputPath": result.get("inputPath"),
        "outputPath": result.get("outputPath"),
        "transcodeProfile": result.get("transcodeProfile") or {},
    }
    row.extracted_at = datetime.now(UTC)


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
