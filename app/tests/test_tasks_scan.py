from __future__ import annotations

from pathlib import Path

from fileflash.tasks.scan import run_dangerous_file_scan


def test_scan_marks_normal_text_file_as_clean(tmp_path: Path):
    target = tmp_path / "readme.txt"
    target.write_text("hello fileflash", encoding="utf-8")

    result = run_dangerous_file_scan({"localPath": str(target)})

    assert result["scanResult"] == "clean"
    assert result["detectedSignals"] == []
    assert result["details"]["fileName"] == "readme.txt"


def test_scan_blocks_disguised_executable(tmp_path: Path):
    target = tmp_path / "invoice.pdf.exe"
    target.write_bytes(b"MZ\x00\x00PE")

    result = run_dangerous_file_scan({"localPath": str(target)})

    assert result["scanResult"] == "blocked"
    assert "dangerous-extension:.exe" in result["detectedSignals"]
    assert "double-extension:.pdf.exe" in result["detectedSignals"]
    assert "magic:portable-executable" in result["detectedSignals"]
