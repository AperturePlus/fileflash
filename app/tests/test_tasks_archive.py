from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from src.tasks.archive import (
    ArchiveLimits,
    _detect_archive_format,
    _extract_tar,
    _extract_zip,
    _preview_tar,
    _preview_zip,
    _sanitize_archive_member_path,
)


def _default_limits(**overrides: int) -> ArchiveLimits:
    base = {
        "preview_max_entries": 2000,
        "extract_max_entries": 100,
        "extract_max_total_bytes": 1024 * 1024,
        "extract_max_file_bytes": 1024 * 1024,
    }
    base.update(overrides)
    return ArchiveLimits(**base)


def test_detect_archive_format_supports_common_suffixes():
    assert _detect_archive_format("demo.zip") == "zip"
    assert _detect_archive_format("demo.7z") == "7z"
    assert _detect_archive_format("demo.tar") == "tar"
    assert _detect_archive_format("demo.tar.gz") == "tar.gz"
    assert _detect_archive_format("demo.tgz") == "tar.gz"


def test_sanitize_archive_member_path_rejects_traversal_and_absolute():
    assert _sanitize_archive_member_path("../evil.txt", is_dir=False) is None
    assert _sanitize_archive_member_path("a/../evil.txt", is_dir=False) is None
    assert _sanitize_archive_member_path("/etc/passwd", is_dir=False) is None
    assert _sanitize_archive_member_path("C:\\evil.txt", is_dir=False) is None
    assert _sanitize_archive_member_path("", is_dir=False) is None


def test_preview_zip_counts_and_truncates(tmp_path: Path):
    archive_path = tmp_path / "demo.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("docs/", "")
        zf.writestr("docs/readme.txt", "hello")
        zf.writestr("image.png", b"\x89PNG\r\n")

    entries, summary = _preview_zip(archive_path=archive_path, max_entries=1)
    assert len(entries) == 1
    assert summary["totalEntries"] == 3
    assert summary["fileCount"] == 2
    assert summary["dirCount"] == 1
    assert summary["truncated"] is True


def test_extract_zip_skips_unsafe_member(tmp_path: Path):
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("../evil.txt", "nope")
        zf.writestr("ok.txt", "yes")

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    limits = ArchiveLimits(
        preview_max_entries=2000,
        extract_max_entries=100,
        extract_max_total_bytes=1024 * 1024,
        extract_max_file_bytes=1024 * 1024,
    )

    extracted_files, extracted_dirs, skipped = _extract_zip(
        archive_path=archive_path,
        extract_dir=out_dir,
        limits=limits,
    )

    assert skipped == 1
    assert any(rel == "ok.txt" for rel, _ in extracted_files)
    assert (out_dir / "ok.txt").exists()
    assert not (tmp_path / "evil.txt").exists()
    assert extracted_dirs == set()


def test_preview_tar_counts(tmp_path: Path):
    archive_path = tmp_path / "demo.tar"
    with tarfile.open(archive_path, "w") as tf:
        info = tarfile.TarInfo("dir/")
        info.type = tarfile.DIRTYPE
        tf.addfile(info)

        content = b"hello"
        file_info = tarfile.TarInfo("dir/readme.txt")
        file_info.size = len(content)
        tf.addfile(file_info, fileobj=io.BytesIO(content))

    entries, summary = _preview_tar(archive_path=archive_path, max_entries=2000)
    assert summary["totalEntries"] == 2
    assert summary["fileCount"] == 1
    assert summary["dirCount"] >= 1
    assert any(entry["isDir"] for entry in entries)


def test_extract_tar_skips_unsafe_member(tmp_path: Path):
    archive_path = tmp_path / "unsafe.tar"
    with tarfile.open(archive_path, "w") as tf:
        content = b"x"
        evil = tarfile.TarInfo("../evil.txt")
        evil.size = len(content)
        tf.addfile(evil, fileobj=io.BytesIO(content))

        ok = tarfile.TarInfo("ok.txt")
        ok.size = len(content)
        tf.addfile(ok, fileobj=io.BytesIO(content))

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    limits = ArchiveLimits(
        preview_max_entries=2000,
        extract_max_entries=100,
        extract_max_total_bytes=1024 * 1024,
        extract_max_file_bytes=1024 * 1024,
    )

    extracted_files, _extracted_dirs, skipped = _extract_tar(
        archive_path=archive_path,
        extract_dir=out_dir,
        limits=limits,
    )

    assert skipped == 1
    assert any(rel == "ok.txt" for rel, _ in extracted_files)
    assert (out_dir / "ok.txt").exists()
    assert not (tmp_path / "evil.txt").exists()


def test_sanitize_archive_rejects_long_segment():
    long_part = "a" * 300
    assert _sanitize_archive_member_path(f"dir/{long_part}/file.txt", is_dir=False) is None


def test_extract_zip_enforces_entry_count_limit(tmp_path: Path):
    archive_path = tmp_path / "too_many.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        for index in range(5):
            zf.writestr(f"file-{index}.txt", b"x")

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    with pytest.raises(ValueError, match="too many entries"):
        _extract_zip(
            archive_path=archive_path,
            extract_dir=out_dir,
            limits=_default_limits(extract_max_entries=2),
        )


def test_extract_zip_enforces_total_size_limit(tmp_path: Path):
    archive_path = tmp_path / "too_big.zip"
    payload = b"x" * 2048
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("a.bin", payload)
        zf.writestr("b.bin", payload)

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    with pytest.raises(ValueError, match="too large"):
        _extract_zip(
            archive_path=archive_path,
            extract_dir=out_dir,
            limits=_default_limits(extract_max_total_bytes=2048),
        )


def test_extract_zip_enforces_single_file_limit(tmp_path: Path):
    archive_path = tmp_path / "fat_member.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("big.bin", b"x" * 4096)

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    with pytest.raises(ValueError, match="member too large"):
        _extract_zip(
            archive_path=archive_path,
            extract_dir=out_dir,
            limits=_default_limits(
                extract_max_entries=10,
                extract_max_total_bytes=10 * 1024,
                extract_max_file_bytes=1024,
            ),
        )


def test_preview_tar_gz_counts(tmp_path: Path):
    archive_path = tmp_path / "demo.tar.gz"
    content = b"hello"
    with tarfile.open(archive_path, "w:gz") as tf:
        info = tarfile.TarInfo("readme.txt")
        info.size = len(content)
        tf.addfile(info, fileobj=io.BytesIO(content))

    assert _detect_archive_format("demo.tar.gz") == "tar.gz"
    entries, summary = _preview_tar(archive_path=archive_path, max_entries=2000)
    assert summary["fileCount"] == 1
    assert entries[0]["path"] == "readme.txt"
    assert summary["truncated"] is False


def test_preview_7z_reports_entries(tmp_path: Path):
    py7zr = pytest.importorskip("py7zr")

    payload_dir = tmp_path / "src"
    payload_dir.mkdir()
    (payload_dir / "readme.txt").write_text("hello")

    archive_path = tmp_path / "demo.7z"
    with py7zr.SevenZipFile(archive_path, "w") as archive:
        archive.writeall(payload_dir, "root")

    from src.tasks.archive import _preview_7z

    entries, summary = _preview_7z(archive_path=archive_path, max_entries=2000)
    assert summary["totalEntries"] >= 1
    assert any(entry["path"].endswith("readme.txt") for entry in entries)
