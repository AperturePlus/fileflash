from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from fileflash.core.errors import ApiError
from fileflash.core.settings import Settings
from fileflash.models.enums import UploadPartStatus, UploadTaskStatus
from fileflash.models.tables_storage import File, FileMediaMetadata, StorageObject, UploadTask, UploadTaskPart
from fileflash.s3.minio_client import ObjectStat, ObjectStorageAuthError, ObjectWriteResult
from fileflash.schemas.file import MergeChunksRequest, MergeChunksResponse, UploadPreflightRequest
from fileflash.services.upload import UploadService


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
        now = datetime.now(UTC)
        for index, obj in enumerate(self.added, start=1):
            if isinstance(obj, StorageObject) and obj.object_id is None:
                obj.object_id = index
            if isinstance(obj, UploadTask) and obj.task_id is None:
                obj.task_id = index
            if isinstance(obj, File) and obj.file_id is None:
                obj.file_id = index
            if isinstance(obj, File) and obj.created_at is None:
                obj.created_at = now
            if isinstance(obj, File) and obj.updated_at is None:
                obj.updated_at = now

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
    jobs = SimpleNamespace(
        enqueue=AsyncMock(),
        enqueue_transcode_job=AsyncMock(),
    )
    service = UploadService(db=session, settings=settings or make_settings(), storage=storage, jobs=jobs)
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
async def test_preflight_returns_503_when_storage_is_unavailable(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service, storage = make_service(session)
    storage.ensure_bucket = AsyncMock(side_effect=ObjectStorageAuthError("bad credentials"))
    cleanup_mock = AsyncMock()
    monkeypatch.setattr(service, "_cleanup_expired_tasks", cleanup_mock)

    with pytest.raises(ApiError) as exc:
        await service.preflight(
            user_id=3,
            payload=UploadPreflightRequest(
                fileHash="c" * 64,
                fileName="broken.txt",
                fileSize=16,
                mimeType="text/plain",
                parentId="root",
            ),
        )

    assert exc.value.status_code == 503
    assert exc.value.code == 503
    assert exc.value.message == "Object storage unavailable"
    cleanup_mock.assert_not_awaited()


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


@pytest.mark.asyncio
async def test_merge_is_idempotent_for_completed_session(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service, storage = make_service(session)
    completed_task = UploadTask(
        task_id=30,
        user_id=8,
        folder_id=12,
        file_name="final.bin",
        mime_type="application/octet-stream",
        bucket_name="fileflash",
        object_key="objects/u8/final",
        object_hash=("c" * 32) + (" " * 32),
        total_size=1024,
        chunk_size=512,
        upload_id="upload-complete",
        status=UploadTaskStatus.COMPLETED,
        expired_at=datetime.now(UTC) + timedelta(hours=1),
    )
    file_row = File(
        file_id=701,
        uploader_id=8,
        owner_id=8,
        folder_id=12,
        file_name="final.bin",
        storage_object_id=91,
        file_size=1024,
        mime_type="application/octet-stream",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    monkeypatch.setattr(service, "_get_task_for_update", AsyncMock(return_value=completed_task))
    monkeypatch.setattr(service, "_find_completed_file_for_task", AsyncMock(return_value=file_row))

    response = await service.merge_chunks(
        user_id=8,
        upload_id="upload-complete",
        payload=MergeChunksRequest(
            fileHash="c" * 64,
            fileName="final.bin",
            mimeType="application/octet-stream",
            parentId="12",
        ),
    )

    assert response.file_id == "701"
    assert response.file_name == "final.bin"
    assert response.object_hash == "c" * 32
    storage.compose_object.assert_not_awaited()


@pytest.mark.asyncio
async def test_merge_allows_padded_task_hash(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service, storage = make_service(session)
    task = UploadTask(
        task_id=40,
        user_id=3,
        folder_id=1,
        file_name="report.txt",
        mime_type="text/plain",
        bucket_name="fileflash",
        object_key="objects/u3/report",
        object_hash=("a" * 32) + (" " * 32),
        total_size=4,
        chunk_size=2,
        upload_id="upload-pad-hash",
        status=UploadTaskStatus.UPLOADING,
        expired_at=datetime.now(UTC) + timedelta(hours=1),
    )
    parts = [
        UploadTaskPart(task_id=40, part_number=0, part_size=2, status=UploadPartStatus.UPLOADED),
        UploadTaskPart(task_id=40, part_number=1, part_size=2, status=UploadPartStatus.UPLOADED),
    ]
    session.scalars_queue = [parts]

    monkeypatch.setattr(service, "_get_task_for_update", AsyncMock(return_value=task))
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=1))
    monkeypatch.setattr(service, "_find_conflict_file", AsyncMock(return_value=None))
    monkeypatch.setattr(
        service,
        "_find_storage_object",
        AsyncMock(return_value=SimpleNamespace(object_id=10, object_key=task.object_key)),
    )
    storage.compute_object_hash = AsyncMock(return_value="a" * 32)

    response = await service.merge_chunks(
        user_id=3,
        upload_id="upload-pad-hash",
        payload=MergeChunksRequest(
            fileHash="a" * 32,
            fileName="report.txt",
            mimeType="text/plain",
            parentId="1",
        ),
    )

    assert response.file_name == "report.txt"
    assert response.object_hash == "a" * 32


@pytest.mark.asyncio
async def test_merge_normalizes_generic_video_mime_on_write(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service, storage = make_service(session)
    task = UploadTask(
        task_id=43,
        user_id=6,
        folder_id=1,
        file_name="clip.mp4",
        mime_type="application/octet-stream",
        bucket_name="fileflash",
        object_key="objects/u6/clip",
        object_hash="f" * 64,
        total_size=4,
        chunk_size=2,
        upload_id="upload-video-mime",
        status=UploadTaskStatus.UPLOADING,
        expired_at=datetime.now(UTC) + timedelta(hours=1),
    )
    parts = [
        UploadTaskPart(task_id=43, part_number=0, part_size=2, status=UploadPartStatus.UPLOADED),
        UploadTaskPart(task_id=43, part_number=1, part_size=2, status=UploadPartStatus.UPLOADED),
    ]
    session.scalars_queue = [parts]

    monkeypatch.setattr(service, "_get_task_for_update", AsyncMock(return_value=task))
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=1))
    monkeypatch.setattr(service, "_find_conflict_file", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_find_storage_object", AsyncMock(return_value=None))
    storage.compute_object_hash = AsyncMock(return_value="f" * 64)

    response = await service.merge_chunks(
        user_id=6,
        upload_id="upload-video-mime",
        payload=MergeChunksRequest(
            fileHash="f" * 64,
            fileName="clip.mp4",
            mimeType="application/octet-stream",
            parentId="1",
        ),
    )

    created_file = next(obj for obj in session.added if isinstance(obj, File))
    created_storage = next(obj for obj in session.added if isinstance(obj, StorageObject))

    assert created_storage.content_type == "video/mp4"
    assert created_file.mime_type == "video/mp4"
    assert task.mime_type == "video/mp4"
    assert response.mime_type == "video/mp4"


@pytest.mark.asyncio
async def test_merge_logs_warning_for_incomplete_chunks(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    session = DummySession()
    service, _storage = make_service(session)
    task = UploadTask(
        task_id=41,
        user_id=3,
        folder_id=1,
        file_name="partial.txt",
        mime_type="text/plain",
        bucket_name="fileflash",
        object_key="objects/u3/partial",
        object_hash="d" * 32,
        total_size=4,
        chunk_size=2,
        upload_id="upload-incomplete",
        status=UploadTaskStatus.UPLOADING,
        expired_at=datetime.now(UTC) + timedelta(hours=1),
    )
    parts = [UploadTaskPart(task_id=41, part_number=0, part_size=2, status=UploadPartStatus.UPLOADED)]
    session.scalars_queue = [parts]

    monkeypatch.setattr(service, "_get_task_for_update", AsyncMock(return_value=task))
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=1))
    monkeypatch.setattr(service, "_find_conflict_file", AsyncMock(return_value=None))
    caplog.set_level(logging.WARNING, logger="fileflash.services.upload")

    with pytest.raises(ApiError) as exc:
        await service.merge_chunks(
            user_id=3,
            upload_id="upload-incomplete",
            payload=MergeChunksRequest(
                fileHash="d" * 32,
                fileName="partial.txt",
                mimeType="text/plain",
                parentId="1",
            ),
        )

    assert exc.value.status_code == 400
    assert "upload-incomplete" in caplog.text
    assert "incomplete chunks" in caplog.text


@pytest.mark.asyncio
async def test_merge_logs_warning_for_non_continuous_chunks(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    session = DummySession()
    service, _storage = make_service(session)
    task = UploadTask(
        task_id=42,
        user_id=4,
        folder_id=1,
        file_name="sparse.txt",
        mime_type="text/plain",
        bucket_name="fileflash",
        object_key="objects/u4/sparse",
        object_hash="e" * 32,
        total_size=4,
        chunk_size=2,
        upload_id="upload-non-contiguous",
        status=UploadTaskStatus.UPLOADING,
        expired_at=datetime.now(UTC) + timedelta(hours=1),
    )
    parts = [
        UploadTaskPart(task_id=42, part_number=0, part_size=2, status=UploadPartStatus.UPLOADED),
        UploadTaskPart(task_id=42, part_number=2, part_size=2, status=UploadPartStatus.UPLOADED),
    ]
    session.scalars_queue = [parts]

    monkeypatch.setattr(service, "_get_task_for_update", AsyncMock(return_value=task))
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=1))
    monkeypatch.setattr(service, "_find_conflict_file", AsyncMock(return_value=None))
    caplog.set_level(logging.WARNING, logger="fileflash.services.upload")

    with pytest.raises(ApiError) as exc:
        await service.merge_chunks(
            user_id=4,
            upload_id="upload-non-contiguous",
            payload=MergeChunksRequest(
                fileHash="e" * 32,
                fileName="sparse.txt",
                mimeType="text/plain",
                parentId="1",
            ),
        )

    assert exc.value.status_code == 400
    assert "upload-non-contiguous" in caplog.text
    assert "non-continuous chunks" in caplog.text


@pytest.mark.asyncio
async def test_merge_enqueues_transcode_for_video_and_sets_queued_metadata(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service, storage = make_service(session)
    task = UploadTask(
        task_id=50,
        user_id=9,
        folder_id=1,
        file_name="movie.mp4",
        mime_type="video/mp4",
        bucket_name="fileflash",
        object_key="objects/u9/movie",
        object_hash="1" * 64,
        total_size=4,
        chunk_size=2,
        upload_id="upload-video-transcode",
        status=UploadTaskStatus.UPLOADING,
        expired_at=datetime.now(UTC) + timedelta(hours=1),
    )
    parts = [
        UploadTaskPart(task_id=50, part_number=0, part_size=2, status=UploadPartStatus.UPLOADED),
        UploadTaskPart(task_id=50, part_number=1, part_size=2, status=UploadPartStatus.UPLOADED),
    ]
    session.scalars_queue = [parts]

    monkeypatch.setattr(service, "_get_task_for_update", AsyncMock(return_value=task))
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=1))
    monkeypatch.setattr(service, "_find_conflict_file", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_find_storage_object", AsyncMock(return_value=None))
    storage.compute_object_hash = AsyncMock(return_value="1" * 64)

    response = await service.merge_chunks(
        user_id=9,
        upload_id="upload-video-transcode",
        payload=MergeChunksRequest(
            fileHash="1" * 64,
            fileName="movie.mp4",
            mimeType="video/mp4",
            parentId="1",
        ),
    )

    assert response.file_name == "movie.mp4"
    created_metadata = next(obj for obj in session.added if isinstance(obj, FileMediaMetadata))
    assert created_metadata.extra_metadata["transcode"]["status"] == "queued"
    service.jobs.enqueue_transcode_job.assert_awaited_once()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_merge_transcode_enqueue_failure_does_not_fail_upload(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service, storage = make_service(session)
    service.jobs.enqueue_transcode_job = AsyncMock(  # type: ignore[union-attr]
        side_effect=ApiError(status_code=503, code=503, message="Job queue unavailable")
    )
    task = UploadTask(
        task_id=51,
        user_id=9,
        folder_id=1,
        file_name="audio.mp3",
        mime_type="audio/mpeg",
        bucket_name="fileflash",
        object_key="objects/u9/audio",
        object_hash="2" * 64,
        total_size=4,
        chunk_size=2,
        upload_id="upload-audio-transcode",
        status=UploadTaskStatus.UPLOADING,
        expired_at=datetime.now(UTC) + timedelta(hours=1),
    )
    parts = [
        UploadTaskPart(task_id=51, part_number=0, part_size=2, status=UploadPartStatus.UPLOADED),
        UploadTaskPart(task_id=51, part_number=1, part_size=2, status=UploadPartStatus.UPLOADED),
    ]
    session.scalars_queue = [parts]

    monkeypatch.setattr(service, "_get_task_for_update", AsyncMock(return_value=task))
    monkeypatch.setattr(service, "_resolve_folder_id", AsyncMock(return_value=1))
    monkeypatch.setattr(service, "_find_conflict_file", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_find_storage_object", AsyncMock(return_value=None))
    storage.compute_object_hash = AsyncMock(return_value="2" * 64)

    response = await service.merge_chunks(
        user_id=9,
        upload_id="upload-audio-transcode",
        payload=MergeChunksRequest(
            fileHash="2" * 64,
            fileName="audio.mp3",
            mimeType="audio/mpeg",
            parentId="1",
        ),
    )

    assert response.file_name == "audio.mp3"
    created_metadata = next(obj for obj in session.added if isinstance(obj, FileMediaMetadata))
    assert created_metadata.extra_metadata["transcode"]["status"] == "failed"


@pytest.mark.asyncio
async def test_enqueue_merge_job_uses_normalized_payload(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service, _storage = make_service(session)
    fake_job = SimpleNamespace(job_id=1234, task_type="task.upload_merge", status="pending")
    service.jobs.enqueue = AsyncMock(return_value=fake_job)  # type: ignore[union-attr]

    payload = MergeChunksRequest(
        fileHash="A" * 64,
        fileName="movie.mp4",
        mimeType="video/mp4",
        parentId="root",
        conflictStrategy="rename",
    )
    job = await service.enqueue_merge_job(
        user_id=7,
        upload_id="upload-merge-job",
        payload=payload,
    )

    assert job is fake_job
    service.jobs.enqueue.assert_awaited_once()  # type: ignore[union-attr]
    _db, kwargs = service.jobs.enqueue.await_args.args, service.jobs.enqueue.await_args.kwargs  # type: ignore[union-attr]
    assert kwargs["task_type"] == "task.upload_merge"
    assert kwargs["requested_by"] == 7
    assert kwargs["idempotency_key"].startswith("upload:7:upload-merge-job:merge:")
    assert kwargs["payload"]["userId"] == 7
    assert kwargs["payload"]["uploadId"] == "upload-merge-job"
    assert kwargs["payload"]["mergeRequest"]["fileHash"] == ("a" * 64)


@pytest.mark.asyncio
async def test_execute_merge_job_calls_merge_chunks(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service, _storage = make_service(session)
    expected = MergeChunksResponse(
        fileId="901",
        fileName="report.pdf",
        fileSize=1024,
        mimeType="application/pdf",
        folderId="root",
        objectHash="f" * 64,
        createdAt=datetime.now(UTC),
        downloadUrl="/api/v1/files/901/download",
    )
    merge_mock = AsyncMock(return_value=expected)
    monkeypatch.setattr(service, "merge_chunks", merge_mock)

    result = await service.execute_merge_job(
        payload={
            "userId": 99,
            "uploadId": "upload-exec-1",
            "mergeRequest": {
                "fileHash": "f" * 64,
                "fileName": "report.pdf",
                "mimeType": "application/pdf",
                "parentId": "root",
            },
        }
    )

    merge_mock.assert_awaited_once()
    assert result["fileId"] == "901"
    assert result["fileName"] == "report.pdf"
    assert result["downloadUrl"] == "/api/v1/files/901/download"
    assert isinstance(result["createdAt"], str)
    assert datetime.fromisoformat(result["createdAt"].replace("Z", "+00:00")) == expected.created_at
