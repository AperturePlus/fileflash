from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import get_current_user, get_download_rate_limit_service, get_file_service
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.models.enums import (
    FileStatus,
    FolderStatus,
    FolderType,
    UploadStatus,
    UserRole,
    UserStatus,
)
from fileflash.models.tables_identity import User
from fileflash.models.tables_storage import File, FileMediaMetadata, Folder, StorageObject
from fileflash.routers.files import router as files_router
from fileflash.schemas.file import BatchDownloadRequest, BatchFilesRequest
from fileflash.services.file import BatchDownloadPlan, DownloadStreamResult, FileService


class DummyStorage:
    async def iter_object(self, *, object_key: str, bucket_name: str | None = None):  # noqa: ARG002
        yield b"abcdefghij"

    async def iter_object_range(
        self,
        *,
        object_key: str,
        start: int,
        end: int,
        bucket_name: str | None = None,
    ):  # noqa: ARG002
        yield bytes(range(start, end + 1))

    async def object_exists(self, *, bucket_name: str, object_key: str):  # noqa: ARG002
        return False


class DummySession:
    def __init__(self) -> None:
        self.commit = AsyncMock()
        self.execute = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock(return_value=[])
        self.get = AsyncMock()
        self.flush = AsyncMock()
        self.delete = AsyncMock()


class ResultRows:
    def __init__(self, rows) -> None:  # noqa: ANN001
        self._rows = rows

    def all(self):  # noqa: ANN201
        return self._rows


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


def make_user(*, role: UserRole = UserRole.USER) -> User:
    return User(
        user_id=1,
        username="alice",
        email="alice@example.com",
        password_hash="x",
        role=role,
        status=UserStatus.ACTIVE,
        email_verified=True,
        storage_limit=1024,
        storage_used=0,
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
async def test_get_preview_stream_prefers_transcoded_object_when_ready(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    storage = DummyStorage()
    service = FileService(db=session, storage=storage)

    file_row = make_file_row(file_id=11, file_name="preview.mkv")
    file_row.file_ext = "mkv"
    file_row.mime_type = "video/x-matroska"
    file_row.storage_object_id = 101
    source_object = StorageObject(
        object_id=101,
        bucket_name="fileflash",
        object_key="objects/u1/source",
        object_size=256,
        upload_status=UploadStatus.ACTIVE,
        content_type="video/mp4",
    )
    optimized_object = StorageObject(
        object_id=102,
        bucket_name="fileflash",
        object_key="optimized/transcode/v1/object-101/source-mp4-v1.mp4",
        object_size=128,
        upload_status=UploadStatus.ACTIVE,
        content_type="video/mp4",
    )
    metadata = FileMediaMetadata(source_object_id=101)
    metadata.extra_metadata = {
        "transcode": {
            "status": "ready",
            "mediaType": "video",
            "optimizedBucketName": optimized_object.bucket_name,
            "optimizedObjectKey": optimized_object.object_key,
            "optimizedMimeType": "video/mp4",
            "updatedAt": datetime.now(UTC).isoformat(),
        }
    }
    metadata.extracted_at = datetime.now(UTC)

    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    session.get = AsyncMock(return_value=source_object)
    session.scalar = AsyncMock(side_effect=[metadata, optimized_object])

    result = await service.get_preview_stream(user_id=1, file_id="11", range_header=None)
    assert result.status_code == 200
    assert result.content_type == "video/mp4"
    assert result.headers["Content-Length"] == "128"


@pytest.mark.asyncio
async def test_get_preview_stream_falls_back_to_source_when_transcoded_missing(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    storage = DummyStorage()
    service = FileService(db=session, storage=storage)

    file_row = make_file_row(file_id=12, file_name="preview.mp4")
    file_row.file_ext = "mp4"
    file_row.mime_type = "video/mp4"
    file_row.storage_object_id = 201
    source_object = StorageObject(
        object_id=201,
        bucket_name="fileflash",
        object_key="objects/u1/source-2",
        object_size=512,
        upload_status=UploadStatus.ACTIVE,
        content_type="video/mp4",
    )
    metadata = FileMediaMetadata(source_object_id=201)
    metadata.extra_metadata = {
        "transcode": {
            "status": "ready",
            "mediaType": "video",
            "optimizedBucketName": "fileflash",
            "optimizedObjectKey": "optimized/not-found.mp4",
            "optimizedMimeType": "video/mp4",
            "updatedAt": datetime.now(UTC).isoformat(),
        }
    }
    metadata.extracted_at = datetime.now(UTC)

    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    session.get = AsyncMock(return_value=source_object)
    session.scalar = AsyncMock(side_effect=[metadata, None])
    monkeypatch.setattr(service.storage, "object_exists", AsyncMock(return_value=False))

    result = await service.get_preview_stream(user_id=1, file_id="12", range_header=None)
    assert result.status_code == 200
    assert result.headers["Content-Length"] == "512"


@pytest.mark.asyncio
async def test_batch_download_plan_estimates_source_file_size() -> None:
    session = DummySession()
    storage = DummyStorage()
    service = FileService(db=session, storage=storage)
    file_row = make_file_row(file_id=7, file_name="archive.bin")
    file_row.storage_object_id = 99
    storage_object = StorageObject(
        object_id=99,
        bucket_name="fileflash",
        object_key="objects/u1/archive",
        object_size=512,
        upload_status=UploadStatus.ACTIVE,
        content_type="application/octet-stream",
    )
    session.scalars = AsyncMock(return_value=[file_row])
    session.execute = AsyncMock(return_value=ResultRows([(file_row, storage_object)]))

    plan = await service.create_batch_download_plan(
        user_id=1,
        payload=BatchDownloadRequest(fileIds=["7"]),
    )

    assert plan.estimated_bytes == 512
    assert plan.files[0][2] == "archive.bin"


class StubDownloadLimiter:
    def __init__(self, *, deny: bool = False) -> None:
        self.deny = deny
        self.calls: list[tuple[str, int]] = []

    async def enforce_user(self, *, user: User, bytes_count: int) -> None:
        self.calls.append((f"user:{user.user_id}", bytes_count))
        if self.deny and user.role != UserRole.ADMIN:
            raise ApiError(status_code=429, code=429, message="Download rate limit exceeded")

    async def enforce_user_id(self, *, user_id: int, bytes_count: int) -> None:
        self.calls.append((f"user:{user_id}", bytes_count))
        if self.deny:
            raise ApiError(status_code=429, code=429, message="Download rate limit exceeded")


class StubFileRouteService:
    async def get_download_stream(
        self,
        *,
        user_id: int,  # noqa: ARG002
        file_id: str,  # noqa: ARG002
        range_header: str | None,
    ) -> DownloadStreamResult:
        async def _stream():
            yield b"0123456789"

        headers = {"Content-Length": "4" if range_header else "10", "Accept-Ranges": "bytes"}
        if range_header:
            headers["Content-Range"] = "bytes 0-3/10"
        return DownloadStreamResult(
            stream=_stream(),
            filename="demo.txt",
            content_type="text/plain",
            status_code=206 if range_header else 200,
            headers=headers,
        )

    async def get_preview_stream(self, **kwargs) -> DownloadStreamResult:  # noqa: ANN003
        return await self.get_download_stream(**kwargs)

    async def create_batch_download_plan(
        self,
        *,
        user_id: int,  # noqa: ARG002
        payload: BatchDownloadRequest,  # noqa: ARG002
    ) -> BatchDownloadPlan:
        return SimpleNamespace(estimated_bytes=10, files=[object()])  # type: ignore[return-value]

    async def create_batch_download_archive_from_plan(self, *, plan: BatchDownloadPlan):  # noqa: ANN201, ARG002
        tmp = tempfile.NamedTemporaryFile(prefix="fileflash-test-", suffix=".zip", delete=False)
        tmp.write(b"zip")
        tmp.close()
        return tmp.name, "test.zip"


def _files_client(*, role: UserRole, limiter: StubDownloadLimiter) -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(files_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: make_user(role=role)
    app.dependency_overrides[get_file_service] = lambda: StubFileRouteService()
    app.dependency_overrides[get_download_rate_limit_service] = lambda: limiter
    return TestClient(app)


def test_download_route_returns_429_when_limiter_rejects_user() -> None:
    limiter = StubDownloadLimiter(deny=True)
    with _files_client(role=UserRole.USER, limiter=limiter) as client:
        response = client.get("/api/v1/files/1/download")

    assert response.status_code == 429
    assert limiter.calls == [("user:1", 10)]


def test_download_route_preserves_range_response_when_allowed() -> None:
    limiter = StubDownloadLimiter()
    with _files_client(role=UserRole.USER, limiter=limiter) as client:
        response = client.get("/api/v1/files/1/download", headers={"Range": "bytes=0-3"})

    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 0-3/10"
    assert limiter.calls == [("user:1", 4)]


def test_admin_download_route_is_not_rejected_by_user_limiter() -> None:
    limiter = StubDownloadLimiter(deny=True)
    with _files_client(role=UserRole.ADMIN, limiter=limiter) as client:
        response = client.get("/api/v1/files/1/download")

    assert response.status_code == 200
    assert limiter.calls == [("user:1", 10)]


def test_batch_download_route_returns_429_before_archive_when_limited() -> None:
    limiter = StubDownloadLimiter(deny=True)
    with _files_client(role=UserRole.USER, limiter=limiter) as client:
        response = client.post("/api/v1/files/batch-download", json={"fileIds": ["1"]})

    assert response.status_code == 429
    assert limiter.calls == [("user:1", 10)]


def test_admin_batch_download_route_is_not_rejected_by_user_limiter() -> None:
    limiter = StubDownloadLimiter(deny=True)
    with _files_client(role=UserRole.ADMIN, limiter=limiter) as client:
        response = client.post("/api/v1/files/batch-download", json={"fileIds": ["1"]})

    assert response.status_code == 200
    assert response.content == b"zip"


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
