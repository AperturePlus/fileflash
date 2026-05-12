from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from fileflash.tasks.transcode import build_ffmpeg_command, run_media_transcode


def test_build_ffmpeg_command_for_video():
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
    assert command[-1] == "output.mp4"


def test_run_media_transcode_with_mocked_subprocess(monkeypatch, tmp_path: Path):
    input_path = tmp_path / "voice.wav"
    input_path.write_bytes(b"RIFF....WAVEfmt")

    source_probe = {
        "streams": [{"codec_type": "audio", "codec_name": "pcm_s16le", "sample_rate": "44100"}],
        "format": {"duration": "2.5", "bit_rate": "96000"},
    }
    output_probe = {
        "streams": [{"codec_type": "audio", "codec_name": "aac", "sample_rate": "44100"}],
        "format": {"duration": "2.5", "bit_rate": "128000"},
    }
    calls: list[list[str]] = []

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
            payload: dict[str, Any] = source_probe if target.endswith(".wav") else output_probe
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")
        if command[0] == "ffmpeg":
            output_path = Path(command[-1])
            output_path.write_bytes(b"m4a-output")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr("fileflash.tasks.transcode.subprocess.run", fake_run)

    result = run_media_transcode({"inputPath": str(input_path)})

    assert result["mediaType"] == "audio"
    assert result["outputPath"].endswith(".m4a")
    assert result["metadata"]["durationMs"] == 2500
    assert result["metadata"]["audioCodec"] == "aac"
    assert [call[0] for call in calls] == ["ffprobe", "ffmpeg", "ffprobe"]
