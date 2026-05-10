from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.core.errors import ApiError
from src.models.enums import FileStatus, FolderStatus, FolderType
from src.models.tables_storage import File, Folder
from src.schemas.file import BatchFilesRequest, MoveFileRequest, MoveFolderRequest
from src.services.file import FileService
from src.services.folder import FolderService


class DummySession:
    def __init__(self) -> None:
        self.commit = AsyncMock()
        self.execute = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock(return_value=[])


def make_file_row() -> File:
    return File(
        file_id=1,
        uploader_id=1,
        owner_id=1,
        folder_id=10,
        file_name="demo.txt",
        file_ext="txt",
        mime_type="text/plain",
        storage_object_id=9,
        file_size=256,
        is_latest=True,
        status=FileStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_folder_row(*, folder_id: int = 10, folder_type: FolderType = FolderType.NORMAL) -> Folder:
    return Folder(
        folder_id=folder_id,
        owner_id=1,
        parent_folder_id=1,
        folder_name="Docs",
        cached_size=1024,
        status=FolderStatus.ACTIVE,
        folder_type=folder_type,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_move_file_success_with_auto_rename_and_revoke(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = FileService(db=session)
    file_row = make_file_row()

    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=22))
    monkeypatch.setattr(service, "_next_available_file_name", AsyncMock(return_value="demo (1).txt"))
    monkeypatch.setattr(service, "_revoke_active_shares", AsyncMock(return_value=2))

    result = await service.move_file(
        user_id=1,
        file_id="1",
        payload=MoveFileRequest(targetFolderId="22", shareHandling="revoke"),
    )

    assert result.file_id == "1"
    assert result.target_folder_id == "22"
    assert result.final_name == "demo (1).txt"
    assert result.share_handling == "revoke"
    assert result.revoked_share_count == 2
    assert file_row.folder_id == 22
    assert file_row.file_name == "demo (1).txt"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_move_file_keep_does_not_revoke_shares(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = FileService(db=session)
    file_row = make_file_row()
    revoke_mock = AsyncMock(return_value=9)

    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=10))
    monkeypatch.setattr(service, "_next_available_file_name", AsyncMock(return_value="demo.txt"))
    monkeypatch.setattr(service, "_revoke_active_shares", revoke_mock)

    result = await service._move_file_record(
        user_id=1,
        file_id="1",
        target_folder_id="10",
        share_handling="keep",
    )

    assert result.share_handling == "keep"
    assert result.revoked_share_count == 0
    revoke_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_move_folder_rejects_root(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = FileService(db=session)
    root_folder = make_folder_row(folder_type=FolderType.ROOT)

    monkeypatch.setattr(service, "_get_active_folder", AsyncMock(return_value=root_folder))

    with pytest.raises(ApiError) as exc:
        await service._move_folder_record(
            user_id=1,
            folder_id="10",
            target_parent_id="20",
            share_handling="keep",
        )

    assert exc.value.status_code == 400
    assert "Root folder cannot be moved" in exc.value.message


@pytest.mark.asyncio
async def test_move_folder_rejects_cycle(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = FileService(db=session)
    folder_row = make_folder_row(folder_id=10)

    monkeypatch.setattr(service, "_get_active_folder", AsyncMock(return_value=folder_row))
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=20))
    monkeypatch.setattr(service, "_is_descendant_folder", AsyncMock(return_value=True))

    with pytest.raises(ApiError) as exc:
        await service._move_folder_record(
            user_id=1,
            folder_id="10",
            target_parent_id="20",
            share_handling="keep",
        )

    assert exc.value.status_code == 409
    assert "descendant" in exc.value.message


@pytest.mark.asyncio
async def test_move_folder_revoke_shares_for_subtree(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = FileService(db=session)
    folder_row = make_folder_row(folder_id=10)

    monkeypatch.setattr(service, "_get_active_folder", AsyncMock(return_value=folder_row))
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=30))
    monkeypatch.setattr(service, "_is_descendant_folder", AsyncMock(return_value=False))
    monkeypatch.setattr(service, "_next_available_folder_name", AsyncMock(return_value="Docs (1)"))
    monkeypatch.setattr(service, "_collect_folder_subtree", AsyncMock(return_value=([10, 11], [100, 101])))
    monkeypatch.setattr(service, "_revoke_active_shares", AsyncMock(return_value=4))

    result = await service._move_folder_record(
        user_id=1,
        folder_id="10",
        target_parent_id="30",
        share_handling="revoke",
    )

    assert result["folder_id"] == "10"
    assert result["target_parent_id"] == "30"
    assert result["final_name"] == "Docs (1)"
    assert result["revoked_share_count"] == 4
    assert folder_row.parent_folder_id == 30
    assert folder_row.folder_name == "Docs (1)"


@pytest.mark.asyncio
async def test_batch_move_mixed_items_partial_success(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = FileService(db=session)

    async def fake_move_file_record(*, file_id: str, **_: object):
        if file_id == "2":
            raise ApiError(status_code=404, code=404, message="File not found")
        return type(
            "MoveResult",
            (),
            {
                "file_id": file_id,
                "target_folder_id": "root",
                "final_name": f"file-{file_id}.txt",
                "share_handling": "keep",
                "revoked_share_count": 0,
                "moved_at": datetime.now(UTC),
            },
        )()

    async def fake_move_folder_record(*, folder_id: str, **_: object):
        if folder_id == "11":
            raise ApiError(status_code=409, code=409, message="Cannot move a folder into its descendant")
        return {
            "folder_id": folder_id,
            "target_parent_id": "root",
            "final_name": f"folder-{folder_id}",
            "share_handling": "keep",
            "revoked_share_count": 0,
            "moved_at": datetime.now(UTC),
        }

    monkeypatch.setattr(service, "_move_file_record", fake_move_file_record)
    monkeypatch.setattr(service, "_move_folder_record", fake_move_folder_record)

    payload = BatchFilesRequest(
        action="move",
        fileIds=["1", "2"],
        folderIds=["10", "11"],
        targetFolderId="root",
        shareHandling="keep",
    )
    result = await service.batch_files(user_id=1, payload=payload)

    assert result.processed == 4
    assert result.succeeded == 2
    assert result.failed == 2
    assert len(result.results) == 4
    assert any(item.item_type == "file" and not item.success and item.item_id == "2" for item in result.results)
    assert any(item.item_type == "folder" and not item.success and item.item_id == "11" for item in result.results)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_batch_move_requires_target_folder():
    session = DummySession()
    service = FileService(db=session)
    payload = BatchFilesRequest(action="move", fileIds=["1"], folderIds=[])

    with pytest.raises(ApiError) as exc:
        await service.batch_files(user_id=1, payload=payload)

    assert exc.value.status_code == 400
    assert "targetFolderId" in exc.value.message


@pytest.mark.asyncio
async def test_folder_service_move_folder_delegates_to_file_service(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = FolderService(db=session)

    move_mock = AsyncMock(
        return_value={
            "folder_id": "5",
            "target_parent_id": "9",
            "final_name": "Design",
            "share_handling": "revoke",
            "revoked_share_count": 3,
            "moved_at": datetime.now(UTC),
        }
    )
    monkeypatch.setattr("src.services.file.FileService._move_folder_record", move_mock)

    result = await service.move_folder(
        user_id=1,
        folder_id="5",
        payload=MoveFolderRequest(targetParentId="9", shareHandling="revoke"),
    )

    assert result.folder_id == "5"
    assert result.target_parent_id == "9"
    assert result.share_handling == "revoke"
    assert result.revoked_share_count == 3
    session.commit.assert_awaited_once()
