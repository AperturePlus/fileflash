from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..core.settings import get_settings
from ..s3.minio_client import MinioObjectStorageClient

TRANSCODE_PROFILE_VERSION = "mp4-v1"


@dataclass(slots=True)
class TranscodeTaskPayload:
    source_bucket_name: str
    source_object_key: str
    source_object_id: int
    output_bucket_name: str
    output_object_key: str
    file_id: int | None
    requested_by: int | None
    ffmpeg_binary: str
    ffprobe_binary: str
    timeout_seconds: int
    probe_timeout_seconds: int


def run_media_transcode(payload: dict[str, Any] | Any) -> dict[str, Any]:
    parsed = _parse_payload(payload)
    settings = get_settings()
    storage = MinioObjectStorageClient.from_settings(settings)

    with tempfile.TemporaryDirectory(prefix="fileflash-transcode-") as tmp_dir_raw:
        tmp_dir = Path(tmp_dir_raw)
        source_path = tmp_dir / "source"
        source_suffix = Path(parsed.source_object_key).suffix.lower()
        output_suffix = ".mp4"

        try:
            _run_async(
                storage.fget_object(
                    bucket_name=parsed.source_bucket_name,
                    object_key=parsed.source_object_key,
                    file_path=str(source_path),
                )
            )
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Source object not found: {parsed.source_bucket_name}/{parsed.source_object_key}"
            ) from exc

        source_probe = probe_media(
            source_path,
            ffprobe_binary=parsed.ffprobe_binary,
            timeout_seconds=parsed.probe_timeout_seconds,
        )
        media_type = detect_media_type(source_probe)
        if media_type == "audio":
            output_suffix = ".m4a"
        output_path = tmp_dir / f"optimized{output_suffix}"

        ffmpeg_command = build_ffmpeg_command(
            input_path=source_path,
            output_path=output_path,
            media_type=media_type,
            ffmpeg_binary=parsed.ffmpeg_binary,
            payload=payload,
        )
        _run_command(ffmpeg_command, timeout_seconds=parsed.timeout_seconds)

        if not output_path.exists():
            raise RuntimeError(f"Transcode finished but output does not exist: {output_path}")

        upload_result = _run_async(
            storage.fput_object(
                bucket_name=parsed.output_bucket_name,
                object_key=parsed.output_object_key,
                file_path=str(output_path),
                content_type="video/mp4" if media_type == "video" else "audio/mp4",
            )
        )
        output_stat = _run_async(
            storage.stat_object(
                bucket_name=parsed.output_bucket_name,
                object_key=parsed.output_object_key,
            )
        )
        output_probe = probe_media(
            output_path,
            ffprobe_binary=parsed.ffprobe_binary,
            timeout_seconds=parsed.probe_timeout_seconds,
        )
        metadata = extract_media_metadata(output_probe)

        return {
            "mediaType": media_type,
            "sourceObjectId": parsed.source_object_id,
            "sourceBucketName": parsed.source_bucket_name,
            "sourceObjectKey": parsed.source_object_key,
            "outputBucketName": parsed.output_bucket_name,
            "outputObjectKey": parsed.output_object_key,
            "outputObjectEtag": upload_result.etag or output_stat.etag,
            "outputObjectVersionId": upload_result.version_id or output_stat.version_id,
            "outputObjectSize": int(output_stat.size),
            "optimizedMimeType": "video/mp4" if media_type == "video" else "audio/mp4",
            "transcodeProfile": {
                "version": TRANSCODE_PROFILE_VERSION,
                "container": output_suffix.lstrip("."),
                "videoCodec": _first_stream_codec(output_probe, "video"),
                "audioCodec": _first_stream_codec(output_probe, "audio"),
                "sourceExtension": source_suffix.lstrip("."),
            },
            "metadata": metadata,
            "transcodedAt": datetime.now(UTC).isoformat(),
        }


def probe_media(input_path: Path, *, ffprobe_binary: str, timeout_seconds: int) -> dict[str, Any]:
    command = [
        ffprobe_binary,
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(input_path),
    ]
    result = _run_command(command, timeout_seconds=timeout_seconds)
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe JSON parse failed: {exc}") from exc


def detect_media_type(probe_data: dict[str, Any]) -> str:
    streams = probe_data.get("streams", [])
    if any(stream.get("codec_type") == "video" for stream in streams):
        return "video"
    if any(stream.get("codec_type") == "audio" for stream in streams):
        return "audio"
    raise ValueError("Input media does not contain video or audio stream")


def build_ffmpeg_command(
    *,
    input_path: Path,
    output_path: Path,
    media_type: str,
    ffmpeg_binary: str,
    payload: dict[str, Any] | Any,
) -> list[str]:
    audio_bitrate = _coerce_positive_int(payload.get("audioBitrateKbps"), 128)
    command: list[str] = [ffmpeg_binary, "-y", "-i", str(input_path)]

    if media_type == "video":
        video_codec = str(payload.get("videoCodec") or "libx264")
        audio_codec = str(payload.get("audioCodec") or "aac")
        preset = str(payload.get("videoPreset") or "medium")
        crf = _coerce_positive_int(payload.get("videoCrf"), 23)
        command.extend(
            [
                "-vf",
                "scale=w=min(iw\\,1920):h=min(ih\\,1080):force_original_aspect_ratio=decrease,"
                "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-c:v",
                video_codec,
                "-preset",
                preset,
                "-crf",
                str(crf),
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-c:a",
                audio_codec,
                "-b:a",
                f"{audio_bitrate}k",
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
            ]
        )
    else:
        command.extend(
            [
                "-vn",
                "-c:a",
                "aac",
                "-b:a",
                f"{audio_bitrate}k",
                "-movflags",
                "+faststart",
                "-map",
                "0:a:0",
            ]
        )

    command.append(str(output_path))
    return command


def extract_media_metadata(probe_data: dict[str, Any]) -> dict[str, int | str | None]:
    format_data = probe_data.get("format", {})
    streams = probe_data.get("streams", [])

    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)

    duration_ms = _duration_ms_from_format(format_data)
    return {
        "durationMs": duration_ms,
        "width": _safe_int(video_stream.get("width") if video_stream else None),
        "height": _safe_int(video_stream.get("height") if video_stream else None),
        "bitrate": _safe_int(format_data.get("bit_rate")),
        "sampleRate": _safe_int(audio_stream.get("sample_rate") if audio_stream else None),
        "videoCodec": _first_stream_codec(probe_data, "video"),
        "audioCodec": _first_stream_codec(probe_data, "audio"),
    }


def _parse_payload(payload: dict[str, Any] | Any) -> TranscodeTaskPayload:
    source_bucket_name = str(payload.get("sourceBucketName") or "").strip()
    source_object_key = str(payload.get("sourceObjectKey") or "").strip()
    output_bucket_name = str(payload.get("outputBucketName") or source_bucket_name).strip()
    output_object_key = str(payload.get("outputObjectKey") or "").strip()
    source_object_id = _coerce_positive_int(payload.get("sourceObjectId"), 0)
    if not source_bucket_name:
        raise ValueError("Transcode payload requires sourceBucketName")
    if not source_object_key:
        raise ValueError("Transcode payload requires sourceObjectKey")
    if not output_bucket_name:
        raise ValueError("Transcode payload requires outputBucketName")
    if not output_object_key:
        raise ValueError("Transcode payload requires outputObjectKey")
    if source_object_id <= 0:
        raise ValueError("Transcode payload requires sourceObjectId")

    timeout_seconds = _coerce_positive_int(payload.get("timeoutSeconds"), 900)
    probe_timeout_seconds = _coerce_positive_int(
        payload.get("probeTimeoutSeconds"),
        min(60, timeout_seconds),
    )
    file_id = _safe_int(payload.get("fileId"))
    requested_by = _safe_int(payload.get("requestedBy"))

    return TranscodeTaskPayload(
        source_bucket_name=source_bucket_name,
        source_object_key=source_object_key,
        source_object_id=source_object_id,
        output_bucket_name=output_bucket_name,
        output_object_key=output_object_key,
        file_id=file_id,
        requested_by=requested_by,
        ffmpeg_binary=str(payload.get("ffmpegBinary") or "ffmpeg"),
        ffprobe_binary=str(payload.get("ffprobeBinary") or "ffprobe"),
        timeout_seconds=timeout_seconds,
        probe_timeout_seconds=probe_timeout_seconds,
    )


def _run_command(command: list[str], *, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Binary not found for command: {command[0]}") from exc
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)} | {stderr}")
    return result


def _run_async(awaitable: Any) -> Any:
    return asyncio.run(awaitable)


def _safe_int(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _coerce_positive_int(raw: Any, default: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _duration_ms_from_format(format_data: dict[str, Any]) -> int | None:
    raw_duration = format_data.get("duration")
    if raw_duration in (None, ""):
        return None
    try:
        seconds = float(raw_duration)
    except (TypeError, ValueError):
        return None
    return int(seconds * 1000)


def _first_stream_codec(probe_data: dict[str, Any], codec_type: str) -> str | None:
    streams = probe_data.get("streams", [])
    for stream in streams:
        if stream.get("codec_type") == codec_type:
            codec_name = stream.get("codec_name")
            if codec_name:
                return str(codec_name)
    return None
