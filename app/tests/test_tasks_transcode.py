from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from fileflash.tasks.transcode import _run_command, build_ffmpeg_command, run_media_transcode


def test_build_ffmpeg_command_for_video_contains_profile_flags():
    command = build_ffmpeg_command(
        input_path=Path("input.mov"),
        output_path=Path("output.mp4"),
        media_type="video",
        ffmpeg_binary="ffmpeg",
        payload={},
    )

    assert command[:4] == ["ffmpeg", "-y", "-i", "input.mov"]
    assert "-c:v" in command
    assert "libx264" in command
    assert "-movflags" in command
    assert "+faststart" in command
    assert "-pix_fmt" in command
    assert "yuv420p" in command
    assert "-ac" in command
    assert command[command.index("-ac") + 1] == "2"
    assert command[-1] == "output.mp4"


def test_build_ffmpeg_command_for_audio_forces_stereo():
    command = build_ffmpeg_command(
        input_path=Path("input.wav"),
        output_path=Path("output.m4a"),
        media_type="audio",
        ffmpeg_binary="ffmpeg",
        payload={},
    )

    assert command[:4] == ["ffmpeg", "-y", "-i", "input.wav"]
    assert "-vn" in command
    assert "-c:a" in command
    assert "-ac" in command
    assert command[command.index("-ac") + 1] == "2"
    assert command[-1] == "output.m4a"


def test_run_command_raises_value_error_for_deterministic_ffmpeg_encoder_failure(monkeypatch):
    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        _ = (check, capture_output, text, timeout)
        return subprocess.CompletedProcess(
            command,
            returncode=1,
            stdout="",
            stderr='[aac @ 0000020b7eff3d00] Unsupported channel layout "6 channels"\n'
            "Error while opening encoder - maybe incorrect parameters\n"
            "[af#0:1 @ 0000020b003fde00] Task finished with error code: -22 (Invalid argument)",
        )

    monkeypatch.setattr("fileflash.tasks.transcode.subprocess.run", fake_run)

    with pytest.raises(ValueError, match="Command failed"):
        _run_command(["ffmpeg", "-i", "input.mp4", "output.mp4"], timeout_seconds=30)


def test_run_media_transcode_storage_mode_with_mocked_subprocess(monkeypatch, tmp_path: Path):
    source_probe = {
        "streams": [{"codec_type": "audio", "codec_name": "pcm_s16le", "sample_rate": "44100"}],
        "format": {"duration": "2.5", "bit_rate": "96000"},
    }
    output_probe = {
        "streams": [{"codec_type": "audio", "codec_name": "aac", "sample_rate": "44100"}],
        "format": {"duration": "2.5", "bit_rate": "128000"},
    }
    calls: list[list[str]] = []

    class DummyStorage:
        async def fget_object(self, *, bucket_name: str, object_key: str, file_path: str):
            _ = (bucket_name, object_key)
            Path(file_path).write_bytes(b"RIFF....WAVEfmt")
            return SimpleNamespace(etag="src-etag", version_id=None)

        async def fput_object(
            self,
            *,
            bucket_name: str,
            object_key: str,
            file_path: str,
            content_type: str,
        ):
            _ = (bucket_name, object_key, file_path, content_type)
            return SimpleNamespace(etag="out-etag", version_id="v1")

        async def stat_object(self, *, bucket_name: str, object_key: str):
            _ = (bucket_name, object_key)
            return SimpleNamespace(size=128, etag="out-etag", version_id="v1")

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        _ = (check, capture_output, text, timeout)
        calls.append(command)
        if command[0] == "ffprobe":
            target = command[-1]
            payload = source_probe if target.endswith("source") else output_probe
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")
        if command[0] == "ffmpeg":
            output_path = Path(command[-1])
            output_path.write_bytes(b"m4a-output")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr("fileflash.tasks.transcode.subprocess.run", fake_run)
    monkeypatch.setattr(
        "fileflash.tasks.transcode.MinioObjectStorageClient.from_settings",
        lambda _settings: DummyStorage(),
    )

    result = run_media_transcode(
        {
            "sourceBucketName": "fileflash",
            "sourceObjectKey": "objects/u1/voice.wav",
            "sourceObjectId": 99,
            "outputBucketName": "fileflash",
            "outputObjectKey": "optimized/transcode/v1/object-99/voice-mp4-v1.m4a",
        }
    )

    assert result["mediaType"] == "audio"
    assert result["outputObjectKey"].endswith(".m4a")
    assert result["outputObjectSize"] == 128
    assert result["optimizedMimeType"] == "audio/mp4"
    assert result["metadata"]["durationMs"] == 2500
    assert result["metadata"]["audioCodec"] == "aac"
    assert [call[0] for call in calls] == ["ffprobe", "ffmpeg", "ffprobe"]

