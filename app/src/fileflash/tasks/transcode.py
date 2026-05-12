from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def run_media_transcode(payload: dict[str, Any] | Any) -> dict[str, Any]:
    input_path = _resolve_input_path(payload)
    ffmpeg_binary = str(payload.get("ffmpegBinary") or "ffmpeg")
    ffprobe_binary = str(payload.get("ffprobeBinary") or "ffprobe")
    timeout_seconds = _coerce_positive_int(payload.get("timeoutSeconds"), 900)
    probe_timeout_seconds = _coerce_positive_int(
        payload.get("probeTimeoutSeconds"),
        min(60, timeout_seconds),
    )

    source_probe = probe_media(
        input_path,
        ffprobe_binary=ffprobe_binary,
        timeout_seconds=probe_timeout_seconds,
    )
    media_type = detect_media_type(source_probe)
    output_path = resolve_output_path(
        input_path=input_path,
        media_type=media_type,
        raw_output_path=payload.get("outputPath"),
        raw_target_container=payload.get("targetContainer"),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_command = build_ffmpeg_command(
        input_path=input_path,
        output_path=output_path,
        media_type=media_type,
        ffmpeg_binary=ffmpeg_binary,
        payload=payload,
    )
    _run_command(ffmpeg_command, timeout_seconds=timeout_seconds)

    if not output_path.exists():
        raise RuntimeError(f"Transcode finished but output does not exist: {output_path}")

    output_probe = probe_media(
        output_path,
        ffprobe_binary=ffprobe_binary,
        timeout_seconds=probe_timeout_seconds,
    )
    metadata = extract_media_metadata(output_probe)
    return {
        "mediaType": media_type,
        "inputPath": str(input_path),
        "outputPath": str(output_path),
        "transcodeProfile": {
            "container": output_path.suffix.lower().lstrip("."),
            "videoCodec": _first_stream_codec(output_probe, "video"),
            "audioCodec": _first_stream_codec(output_probe, "audio"),
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


def resolve_output_path(
    *,
    input_path: Path,
    media_type: str,
    raw_output_path: Any,
    raw_target_container: Any,
) -> Path:
    if raw_output_path:
        return Path(str(raw_output_path)).expanduser()

    if raw_target_container:
        suffix = "." + str(raw_target_container).strip().lstrip(".").lower()
    elif media_type == "video":
        suffix = ".mp4"
    else:
        suffix = ".m4a"
    return input_path.with_suffix(suffix)


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
                "-c:v",
                video_codec,
                "-preset",
                preset,
                "-crf",
                str(crf),
                "-movflags",
                "+faststart",
                "-c:a",
                audio_codec,
                "-b:a",
                f"{audio_bitrate}k",
            ]
        )
    else:
        preferred_codec = payload.get("audioCodec")
        if preferred_codec:
            audio_codec = str(preferred_codec)
        elif output_path.suffix.lower() == ".mp3":
            audio_codec = "libmp3lame"
        else:
            audio_codec = "aac"
        command.extend(["-vn", "-c:a", audio_codec, "-b:a", f"{audio_bitrate}k"])

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


def _resolve_input_path(payload: dict[str, Any] | Any) -> Path:
    raw_input = str(payload.get("inputPath") or payload.get("localPath") or "").strip()
    if not raw_input:
        raise ValueError("Transcode payload requires inputPath or localPath")
    input_path = Path(raw_input).expanduser()
    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Transcode input not found: {input_path}")
    return input_path


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
