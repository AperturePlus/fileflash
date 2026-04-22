from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.core.errors import ApiError
from src.core.settings import Settings
from src.models.enums import UploadPartStatus, UploadTaskStatus
from src.models.tables_storage import File, UploadTask, UploadTaskPart
from src.s3.minio_client import ObjectStat, ObjectWriteResult
from src.schemas.file import MergeChunksRequest, UploadPreflightRequest
from src.services.upload import UploadService


class DummySession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0
        self.scalars_queue: list[list[object]] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:
        for index, obj in enumerate(self.added, start=1):
            if isinstance(obj, UploadTask) and obj.task_id is None:
                obj.task_id = index
            if isinstance(obj, File) and obj.file_id is None:
                obj.file_id = index

    async def scalar(self, _query: object) -> object | None:
        return None

    async def scalars(self, _query: object) -> list[object]:
        if self.scalars_queue:
            return self.scalars_queue.pop(0)
        return []


def make_settings(**overrides: object) -> Settings:
    payload = {
        "FF_DB_URI": "postgresql://root:pwd@localhost:5432/fileflash",
        "JWT_SECRET_KEY": "unit-test-secret-key-1234567890abcd",
    }
    payload.update(overrides)
    return Settings(**payload)


def make_service(session: DummySession, settings: Settings | None = None) -> tuple[UploadService, SimpleNamespace]:
    storage = SimpleNamespace(
        ensure_bucket=AsyncMock(),
        put_bytes=AsyncMock(return_value=ObjectWriteResult(etag="etag", version_id=None)),
        compose_object=AsyncMock(return_value=ObjectWriteResult(etag="etag-merged", version_id=None)),
        stat_object=AsyncMock(return_value=ObjectStat(size=4, etag="etag-merged", version_id=None, content_type=None)),
        remove_object=AsyncMock(),
        remove_objects=AsyncMock(),
        compute_object_hash=AsyncMock(return_value="0" * 64),
    )
    service = UploadService(db=session, settings=settings or make_settings(), storage=storage)
    return service, storage


@pytest.mark.asyncio
async def test_preflight_returns_complete_when_hash_hit(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service, storage = make_service(session)

    monkeypatch.setattr(service, "_cleanup_expired_tasks", AsyncMock())
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=3))
    monkeypatch.setattr(
        service,
        "_find_storage_object",
        AsyncMock(return_value=SimpleNamespace(object_id=11, object_size=128)),
    )
    monkeypatch.setattr(
        service,
        "_create_file_from_storage_object",
        AsyncMock(return_value=SimpleNamespace(file_id=99)),
    )

    response = await service.preflight(
        user_id=1,
        payload=UploadPreflightRequest(
            fileHash="a" * 64,
            fileName="demo.txt",
            fileSize=128,
            mimeType="text/plain",
            parentId="root",
        ),
    )

    assert response.status == "COMPLETE"
    assert response.file_id == "99"
    assert session.commits == 1
    storage.ensure_bucket.assert_awaited_once()


@pytest.mark.asyncio
async def test_preflight_creates_upload_session_when_no_hit(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service, _storage = make_service(session)

    monkeypatch.setattr(service, "_cleanup_expired_tasks", AsyncMock())
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=7))
    monkeypatch.setattr(service, "_find_storage_object", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_find_active_task", AsyncMock(return_value=None))

    response = await service.preflight(
        user_id=2,
        payload=UploadPreflightRequest(
            fileHash="b" * 64,
            fileName="video.mp4",
            fileSize=1024,
            mimeType="video/mp4",
            parentId="7",
        ),
    )

    assert response.status == "UPLOADING"
    assert response.upload_id is not None
    assert response.chunk_size == 5 * 1024 * 1024
    assert len(session.added) == 1
    assert isinstance(session.added[0], UploadTask)
    assert session.commits == 1


@pytest.mark.asyncio
async def test_upload_chunk_rejects_out_of_range_index(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service, _storage = make_service(session)
    task = UploadTask(
        task_id=1,
        user_id=1,
        folder_id=1,
        file_name="clip.mp4",
        mime_type="video/mp4",
        bucket_name="fileflash",
        object_key="objects/u1/demo",
        object_hash="a" * 64,
        total_size=1024,
        chunk_size=512,
        upload_id="upload-x",
        status=UploadTaskStatus.UPLOADING,
        expired_at=datetime.now(UTC) + timedelta(hours=1),
    )
    monkeypatch.setattr(service, "_get_task_for_update", AsyncMock(return_value=task))

    with pytest.raises(ApiError) as exc:
        await service.upload_chunk(
            user_id=1,
            upload_id="upload-x",
            chunk_index=2,
            chunk_bytes=b"12",
        )

    assert exc.value.status_code == 400
    assert "out of range" in exc.value.message


@pytest.mark.asyncio
async def test_merge_returns_conflict_without_strategy(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service, _storage = make_service(session)
    task = UploadTask(
        task_id=10,
        user_id=1,
        folder_id=1,
        file_name="demo.txt",
        mime_type="text/plain",
        bucket_name="fileflash",
        object_key="objects/u1/abc",
        object_hash="a" * 64,
        total_size=4,
        chunk_size=2,
        upload_id="upload-y",
        status=UploadTaskStatus.UPLOADING,
        expired_at=datetime.now(UTC) + timedelta(hours=1),
    )
    conflict = File(
        file_id=88,
        uploader_id=1,
        owner_id=1,
        folder_id=1,
        file_name="demo.txt",
        storage_object_id=1,
        file_size=10,
    )
    monkeypatch.setattr(service, "_get_task_for_update", AsyncMock(return_value=task))
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=1))
    monkeypatch.setattr(service, "_find_conflict_file", AsyncMock(return_value=conflict))

    with pytest.raises(ApiError) as exc:
        await service.merge_chunks(
            user_id=1,
            upload_id="upload-y",
            payload=MergeChunksRequest(
                fileHash="a" * 64,
                fileName="demo.txt",
                mimeType="text/plain",
                parentId="1",
            ),
        )

    assert exc.value.status_code == 409
    assert isinstance(exc.value.data, dict)
    assert exc.value.data["type"] == "file_name_conflict"


@pytest.mark.asyncio
async def test_merge_marks_failed_on_hash_mismatch(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service, storage = make_service(session)
    task = UploadTask(
        task_id=20,
        user_id=2,
        folder_id=2,
        file_name="asset.bin",
        mime_type="application/octet-stream",
        bucket_name="fileflash",
        object_key="objects/u2/new",
        object_hash="a" * 64,
        total_size=4,
        chunk_size=2,
        upload_id="upload-z",
        status=UploadTaskStatus.UPLOADING,
        expired_at=datetime.now(UTC) + timedelta(hours=1),
    )
    parts = [
        UploadTaskPart(task_id=20, part_number=0, part_size=2, status=UploadPartStatus.UPLOADED),
        UploadTaskPart(task_id=20, part_number=1, part_size=2, status=UploadPartStatus.UPLOADED),
    ]
    session.scalars_queue = [parts]

    monkeypatch.setattr(service, "_get_task_for_update", AsyncMock(return_value=task))
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=2))
    monkeypatch.setattr(service, "_find_conflict_file", AsyncMock(return_value=None))
    storage.compute_object_hash = AsyncMock(return_value="f" * 64)

    with pytest.raises(ApiError) as exc:
        await service.merge_chunks(
            user_id=2,
            upload_id="upload-z",
            payload=MergeChunksRequest(
                fileHash="a" * 64,
                fileName="asset.bin",
                mimeType="application/octet-stream",
                parentId="2",
                conflictStrategy="rename",
            ),
        )

    assert exc.value.status_code == 422
    assert task.status == UploadTaskStatus.FAILED
    assert session.commits == 1
    storage.remove_object.assert_awaited_once()
