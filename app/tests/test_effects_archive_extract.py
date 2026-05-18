from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from fileflash.workers.effects import _apply_archive_extract_effects


class _StubSession:
    def __init__(self) -> None:
        self.scalar = AsyncMock()
        self.flush = AsyncMock()
        self.add = AsyncMock()


@pytest.mark.asyncio
async def test_apply_archive_extract_effects_returns_empty_when_manifest_missing_in_result():
    session = _StubSession()
    extra = await _apply_archive_extract_effects(
        session,  # type: ignore[arg-type]
        payload={"requestedBy": 1, "targetFolderId": "root"},
        result={},
    )
    assert extra == {}


@pytest.mark.asyncio
async def test_apply_archive_extract_effects_returns_empty_when_requested_by_missing(tmp_path: Path):
    session = _StubSession()
    manifest_path = tmp_path / "manifest.jsonl"
    manifest_path.write_text("", encoding="utf-8")
    extra = await _apply_archive_extract_effects(
        session,  # type: ignore[arg-type]
        payload={"targetFolderId": "root"},
        result={"manifestPath": str(manifest_path)},
    )
    assert extra == {}


@pytest.mark.asyncio
async def test_apply_archive_extract_effects_rejects_bad_conflict_strategy(tmp_path: Path):
    session = _StubSession()
    manifest_path = tmp_path / "manifest.jsonl"
    manifest_path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="conflictStrategy"):
        await _apply_archive_extract_effects(
            session,  # type: ignore[arg-type]
            payload={
                "requestedBy": 1,
                "targetFolderId": "root",
                "conflictStrategy": "bogus",
            },
            result={"manifestPath": str(manifest_path)},
        )


@pytest.mark.asyncio
async def test_apply_archive_extract_effects_rejects_missing_target_folder_id(tmp_path: Path):
    session = _StubSession()
    manifest_path = tmp_path / "manifest.jsonl"
    manifest_path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="targetFolderId"):
        await _apply_archive_extract_effects(
            session,  # type: ignore[arg-type]
            payload={"requestedBy": 1, "targetFolderId": "   "},
            result={"manifestPath": str(manifest_path)},
        )


@pytest.mark.asyncio
async def test_apply_archive_extract_effects_requires_manifest_file_to_exist(tmp_path: Path):
    session = _StubSession()
    folder_row = type(
        "Folder",
        (),
        {"folder_id": 42},
    )()
    session.scalar.return_value = folder_row

    missing_manifest = tmp_path / "does_not_exist.jsonl"
    with pytest.raises(FileNotFoundError):
        await _apply_archive_extract_effects(
            session,  # type: ignore[arg-type]
            payload={
                "requestedBy": 1,
                "targetFolderId": "42",
                "createSubfolder": False,
                "conflictStrategy": "rename",
            },
            result={"manifestPath": str(missing_manifest)},
        )


@pytest.mark.asyncio
async def test_apply_archive_extract_effects_skips_file_entries_without_storage_ref(tmp_path: Path):
    session = _StubSession()

    folder_row = type("Folder", (), {"folder_id": 42})()

    # scalar sequence:
    # 1) resolve target folder (_resolve_folder_id) -> folder_row
    # 2) existing-file lookup for file entry -> None
    # 3) existing storage-object lookup -> None (but we skip before it)
    session.scalar.side_effect = [folder_row, None]

    manifest_path = tmp_path / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as fp:
        fp.write(json.dumps({"type": "file", "path": "a.bin", "size": 10}) + "\n")

    extra = await _apply_archive_extract_effects(
        session,  # type: ignore[arg-type]
        payload={
            "requestedBy": 1,
            "targetFolderId": "42",
            "createSubfolder": False,
            "conflictStrategy": "rename",
        },
        result={"manifestPath": str(manifest_path)},
    )

    assert extra["summary"]["extractedFiles"] == 0
    assert extra["summary"]["skippedEntries"] == 1
