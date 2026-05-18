from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.core.errors import ApiError
from src.models.enums import FavoriteItemType, FileStatus, FolderStatus, FolderType
from src.models.tables_access_share import FavoriteItem
from src.models.tables_identity import User
from src.models.tables_storage import File, Folder
from src.schemas.file import (
    BatchFilesRequest,
    CreateFolderRequest,
    FileDetails,
    MoveFileRequest,
    MoveFolderRequest,
    RenameFileRequest,
    RenameFolderRequest,
)
from src.services.file import FileService
from src.services.folder import FolderService


class DummySession:
    def __init__(self) -> None:
        self.commit = AsyncMock()
        self.execute = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock(return_value=[])
        self.get = AsyncMock()
        self.added: list[object] = []
        self.deleted: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def delete(self, obj: object) -> None:
        self.deleted.append(obj)


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


class DummyFolderSession:
    def __init__(self) -> None:
        self.commit = AsyncMock()
        self.scalar = AsyncMock()
        self.get = AsyncMock()
        self.refresh = AsyncMock()
        self.added: list[object] = []
        self.deleted: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def delete(self, obj: object) -> None:
        self.deleted.append(obj)


@pytest.mark.asyncio
async def test_folder_service_create_folder_supports_root_parent(monkeypatch: pytest.MonkeyPatch):
    session = DummyFolderSession()
    service = FolderService(db=session)

    root = Folder(
        folder_id=100,
        owner_id=1,
        parent_folder_id=None,
        folder_name="My Files",
        cached_size=0,
        status=FolderStatus.ACTIVE,
        folder_type=FolderType.ROOT,
    )
    owner = User(user_id=1, username="owner", email="owner@example.com", password_hash="hash")

    session.scalar = AsyncMock(side_effect=[root, None])
    session.get = AsyncMock(return_value=owner)

    response = await service.create_folder(
        user_id=1,
        payload=CreateFolderRequest(folderName="Design", parentFolderId="root"),
    )

    assert response.name == "Design"
    assert response.parent_folder_id == "100"
    session.commit.assert_awaited_once()
    assert any(isinstance(obj, Folder) and obj.folder_name == "Design" for obj in session.added)


@pytest.mark.asyncio
async def test_folder_service_rename_folder_auto_suffix(monkeypatch: pytest.MonkeyPatch):
    session = DummyFolderSession()
    service = FolderService(db=session)
    folder = Folder(
        folder_id=200,
        owner_id=1,
        parent_folder_id=100,
        folder_name="Design",
        cached_size=0,
        status=FolderStatus.ACTIVE,
        folder_type=FolderType.NORMAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    conflict = Folder(
        folder_id=201,
        owner_id=1,
        parent_folder_id=100,
        folder_name="Docs",
        cached_size=0,
        status=FolderStatus.ACTIVE,
        folder_type=FolderType.NORMAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    owner = User(user_id=1, username="owner", email="owner@example.com", password_hash="hash")

    session.scalar = AsyncMock(side_effect=[folder, conflict, None])
    session.get = AsyncMock(return_value=owner)
    monkeypatch.setattr(service, "_starred_folder_ids", AsyncMock(return_value=set()))

    response = await service.rename_folder(
        user_id=1,
        folder_id="200",
        payload=RenameFolderRequest(folderName="Docs"),
    )

    assert response.name == "Docs (1)"
    assert folder.folder_name == "Docs (1)"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_file_service_rename_file_auto_suffix(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = FileService(db=session)
    file_row = make_file_row()

    next_name = AsyncMock(return_value="demo (1).txt")
    expected = FileDetails(
        id="1",
        name="demo (1).txt",
        size=256,
        mimeType="text/plain",
        ownerName="owner",
        updatedAt=datetime.now(UTC),
        createdAt=datetime.now(UTC),
        folderId="10",
        permission="owner",
        isStarred=False,
        status=True,
    )
    get_file_mock = AsyncMock(return_value=expected)

    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    monkeypatch.setattr(service, "_next_available_file_name", next_name)
    monkeypatch.setattr(service, "get_file", get_file_mock)

    result = await service.rename_file(
        user_id=1,
        file_id="1",
        payload=RenameFileRequest(fileName="  demo.txt  "),
    )

    assert result is expected
    assert file_row.file_name == "demo (1).txt"
    next_name.assert_awaited_once()
    assert next_name.await_args.kwargs["original_name"] == "demo.txt"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_file_service_rename_file_rejects_blank_name(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = FileService(db=session)

    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=make_file_row()))
    next_name = AsyncMock(return_value="ignored")
    monkeypatch.setattr(service, "_next_available_file_name", next_name)

    with pytest.raises(ApiError) as exc:
        await service.rename_file(
            user_id=1,
            file_id="1",
            payload=RenameFileRequest.model_construct(file_name="   "),
        )

    assert exc.value.status_code == 400
    assert "fileName cannot be empty" in exc.value.message
    next_name.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_file_service_toggle_file_star_adds_favorite(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = FileService(db=session)
    file_row = make_file_row()
    expected = FileDetails(
        id="1",
        name="demo.txt",
        size=256,
        mimeType="text/plain",
        ownerName="owner",
        updatedAt=datetime.now(UTC),
        createdAt=datetime.now(UTC),
        folderId="10",
        permission="owner",
        isStarred=True,
        status=True,
    )

    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    monkeypatch.setattr(service, "get_file", AsyncMock(return_value=expected))
    session.scalar = AsyncMock(return_value=None)

    result = await service.toggle_file_star(user_id=1, file_id="1", is_starred=True)

    assert result is expected
    assert len(session.added) == 1
    added = session.added[0]
    assert isinstance(added, FavoriteItem)
    assert added.item_type == FavoriteItemType.FILE
    assert added.file_id == 1
    assert added.folder_id is None
    assert session.deleted == []
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_file_service_toggle_file_star_removes_favorite(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = FileService(db=session)
    file_row = make_file_row()
    existing_favorite = FavoriteItem(
        user_id=1,
        item_type=FavoriteItemType.FILE,
        file_id=1,
        folder_id=None,
    )

    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    monkeypatch.setattr(service, "get_file", AsyncMock(return_value=FileDetails(
        id="1",
        name="demo.txt",
        size=256,
        mimeType="text/plain",
        ownerName="owner",
        updatedAt=datetime.now(UTC),
        createdAt=datetime.now(UTC),
        folderId="10",
        permission="owner",
        isStarred=False,
        status=True,
    )))
    session.scalar = AsyncMock(return_value=existing_favorite)

    await service.toggle_file_star(user_id=1, file_id="1", is_starred=False)

    assert session.added == []
    assert session.deleted == [existing_favorite]
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_folder_service_toggle_folder_star_adds_favorite():
    session = DummyFolderSession()
    service = FolderService(db=session)
    folder = make_folder_row(folder_id=200)
    owner = User(user_id=1, username="owner", email="owner@example.com", password_hash="hash")

    session.scalar = AsyncMock(side_effect=[folder, None])
    session.get = AsyncMock(return_value=owner)

    response = await service.toggle_folder_star(user_id=1, folder_id="200", is_starred=True)

    assert response.id == "200"
    assert response.is_starred is True
    assert len(session.added) == 1
    added = session.added[0]
    assert isinstance(added, FavoriteItem)
    assert added.item_type == FavoriteItemType.FOLDER
    assert added.folder_id == 200
    assert added.file_id is None
    assert session.deleted == []
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_folder_service_toggle_folder_star_removes_favorite():
    session = DummyFolderSession()
    service = FolderService(db=session)
    folder = make_folder_row(folder_id=200)
    owner = User(user_id=1, username="owner", email="owner@example.com", password_hash="hash")
    existing_favorite = FavoriteItem(
        user_id=1,
        item_type=FavoriteItemType.FOLDER,
        folder_id=200,
        file_id=None,
    )

    session.scalar = AsyncMock(side_effect=[folder, existing_favorite])
    session.get = AsyncMock(return_value=owner)

    response = await service.toggle_folder_star(user_id=1, folder_id="200", is_starred=False)

    assert response.id == "200"
    assert response.is_starred is False
    assert session.added == []
    assert session.deleted == [existing_favorite]
    session.commit.assert_awaited_once()
