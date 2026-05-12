from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from fileflash.core.errors import ApiError
from fileflash.models.enums import FileStatus, FolderStatus, FolderType, UploadStatus
from fileflash.models.tables_storage import File, Folder, StorageObject
from fileflash.schemas.file import BatchFilesRequest
from fileflash.services.file import FileService


class DummyStorage:
    async def iter_object(self, *, object_key: str):  # noqa: ARG002
        yield b"abcdefghij"

    async def iter_object_range(self, *, object_key: str, start: int, end: int):  # noqa: ARG002
        yield bytes(range(start, end + 1))


class DummySession:
    def __init__(self) -> None:
        self.commit = AsyncMock()
        self.execute = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock(return_value=[])
        self.get = AsyncMock()
        self.flush = AsyncMock()
        self.delete = AsyncMock()


def make_file_row(*, file_id: int = 1, file_name: str = "demo.txt", folder_id: int = 10) -> File:
    return File(
        file_id=file_id,
        uploader_id=1,
        owner_id=1,
        folder_id=folder_id,
        file_name=file_name,
        file_ext="txt",
        mime_type="text/plain",
        storage_object_id=9,
        file_size=256,
        is_latest=True,
        status=FileStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_folder_row(*, folder_id: int = 10, folder_name: str = "Docs") -> Folder:
    return Folder(
        folder_id=folder_id,
        owner_id=1,
        parent_folder_id=1,
        folder_name=folder_name,
        cached_size=1024,
        status=FolderStatus.ACTIVE,
        folder_type=FolderType.NORMAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_get_download_stream_supports_single_range(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    storage = DummyStorage()
    service = FileService(db=session, storage=storage)

    file_row = make_file_row(file_id=7, file_name="chunk.bin")
    file_row.storage_object_id = 99
    storage_object = StorageObject(
        object_id=99,
        bucket_name="fileflash",
        object_key="objects/u1/chunk",
        object_size=256,
        upload_status=UploadStatus.ACTIVE,
        content_type="application/octet-stream",
    )
    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    session.get = AsyncMock(return_value=storage_object)

    result = await service.get_download_stream(
        user_id=1,
        file_id="7",
        range_header="bytes=10-19",
    )

    assert result.status_code == 206
    assert result.headers["Content-Range"] == "bytes 10-19/256"
    assert result.headers["Content-Length"] == "10"


@pytest.mark.asyncio
async def test_get_download_stream_rejects_invalid_range(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    storage = DummyStorage()
    service = FileService(db=session, storage=storage)

    file_row = make_file_row(file_id=7, file_name="chunk.bin")
    file_row.storage_object_id = 99
    storage_object = StorageObject(
        object_id=99,
        bucket_name="fileflash",
        object_key="objects/u1/chunk",
        object_size=256,
        upload_status=UploadStatus.ACTIVE,
        content_type="application/octet-stream",
    )
    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    session.get = AsyncMock(return_value=storage_object)

    with pytest.raises(ApiError) as exc:
        await service.get_download_stream(
            user_id=1,
            file_id="7",
            range_header="bytes=400-450",
        )

    assert exc.value.status_code == 416


@pytest.mark.asyncio
async def test_get_preview_stream_returns_inline_content_disposition(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    storage = DummyStorage()
    service = FileService(db=session, storage=storage)

    file_row = make_file_row(file_id=7, file_name="preview.bin")
    file_row.storage_object_id = 99
    storage_object = StorageObject(
        object_id=99,
        bucket_name="fileflash",
        object_key="objects/u1/preview",
        object_size=256,
        upload_status=UploadStatus.ACTIVE,
        content_type="application/octet-stream",
    )
    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    session.get = AsyncMock(return_value=storage_object)

    result = await service.get_preview_stream(
        user_id=1,
        file_id="7",
        range_header=None,
    )

    assert result.status_code == 200
    assert result.headers["Content-Disposition"] == 'inline; filename="preview.bin"; filename*=UTF-8\'\'preview.bin'
    assert result.headers["Content-Length"] == "256"


@pytest.mark.asyncio
async def test_get_preview_stream_supports_single_range(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    storage = DummyStorage()
    service = FileService(db=session, storage=storage)

    file_row = make_file_row(file_id=7, file_name="preview.bin")
    file_row.storage_object_id = 99
    storage_object = StorageObject(
        object_id=99,
        bucket_name="fileflash",
        object_key="objects/u1/preview",
        object_size=256,
        upload_status=UploadStatus.ACTIVE,
        content_type="application/octet-stream",
    )
    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    session.get = AsyncMock(return_value=storage_object)

    result = await service.get_preview_stream(
        user_id=1,
        file_id="7",
        range_header="bytes=10-19",
    )

    assert result.status_code == 206
    assert result.headers["Content-Disposition"] == 'inline; filename="preview.bin"; filename*=UTF-8\'\'preview.bin'
    assert result.headers["Content-Range"] == "bytes 10-19/256"
    assert result.headers["Content-Length"] == "10"


@pytest.mark.asyncio
async def test_get_preview_stream_infers_video_content_type_from_extension(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    storage = DummyStorage()
    service = FileService(db=session, storage=storage)

    file_row = make_file_row(file_id=7, file_name="trailer.mp4")
    file_row.file_ext = "mp4"
    file_row.mime_type = "application/octet-stream"
    file_row.storage_object_id = 99
    storage_object = StorageObject(
        object_id=99,
        bucket_name="fileflash",
        object_key="objects/u1/trailer",
        object_size=256,
        upload_status=UploadStatus.ACTIVE,
        content_type="application/octet-stream",
    )
    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    session.get = AsyncMock(return_value=storage_object)

    result = await service.get_preview_stream(
        user_id=1,
        file_id="7",
        range_header=None,
    )

    assert result.status_code == 200
    assert result.content_type == "video/mp4"


@pytest.mark.asyncio
async def test_get_preview_stream_handles_unicode_filename_in_content_disposition(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    storage = DummyStorage()
    service = FileService(db=session, storage=storage)

    file_row = make_file_row(file_id=9, file_name="测试文档.pdf")
    file_row.file_ext = "pdf"
    file_row.mime_type = "application/pdf"
    file_row.storage_object_id = 99
    storage_object = StorageObject(
        object_id=99,
        bucket_name="fileflash",
        object_key="objects/u1/cjk-pdf",
        object_size=256,
        upload_status=UploadStatus.ACTIVE,
        content_type="application/pdf",
    )
    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    session.get = AsyncMock(return_value=storage_object)

    result = await service.get_preview_stream(
        user_id=1,
        file_id="9",
        range_header=None,
    )

    assert result.status_code == 200
    assert 'filename*=UTF-8\'\'' in result.headers["Content-Disposition"]
    result.headers["Content-Disposition"].encode("latin-1")


@pytest.mark.asyncio
async def test_get_preview_stream_rejects_invalid_range(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    storage = DummyStorage()
    service = FileService(db=session, storage=storage)

    file_row = make_file_row(file_id=7, file_name="preview.bin")
    file_row.storage_object_id = 99
    storage_object = StorageObject(
        object_id=99,
        bucket_name="fileflash",
        object_key="objects/u1/preview",
        object_size=256,
        upload_status=UploadStatus.ACTIVE,
        content_type="application/octet-stream",
    )
    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    session.get = AsyncMock(return_value=storage_object)

    with pytest.raises(ApiError) as exc:
        await service.get_preview_stream(
            user_id=1,
            file_id="7",
            range_header="bytes=400-450",
        )

    assert exc.value.status_code == 416


@pytest.mark.asyncio
async def test_delete_file_marks_record_deleted(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = FileService(db=session)
    file_row = make_file_row(file_id=3, file_name="archive.zip")

    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))

    result = await service.delete_file(user_id=1, file_id="3")

    assert result.file_id == "3"
    assert result.file_name == "archive.zip"
    assert file_row.status == FileStatus.DELETED
    assert file_row.deleted_at is not None
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_batch_files_delete_supports_files_and_folders(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = FileService(db=session)
    deleted_at = datetime.now(UTC)

    async def fake_delete_file(*, file_id: str, **_: object):
        return make_file_row(file_id=int(file_id), file_name=f"file-{file_id}.txt"), deleted_at

    async def fake_delete_folder(*, folder_id: str, **_: object):
        return make_folder_row(folder_id=int(folder_id), folder_name=f"folder-{folder_id}"), deleted_at

    monkeypatch.setattr(service, "_soft_delete_file_record", fake_delete_file)
    monkeypatch.setattr(service, "_soft_delete_folder_record", fake_delete_folder)

    payload = BatchFilesRequest(
        action="delete",
        fileIds=["1", "2"],
        folderIds=["10"],
    )
    result = await service.batch_files(user_id=1, payload=payload)

    assert result.action == "delete"
    assert result.processed == 3
    assert result.succeeded == 3
    assert result.failed == 0
    session.commit.assert_awaited_once()
