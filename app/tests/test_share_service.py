from __future__ import annotations

import re
from datetime import UTC, datetime
from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.security import create_share_access_token, decode_share_access_token
from fileflash.core.settings import Settings
from fileflash.models.enums import UploadStatus
from fileflash.models.tables_access_share import Share
from fileflash.models.tables_storage import File, FileMediaMetadata, StorageObject
from fileflash.schemas.share import CreateShareRequest, SaveShareRequest, UpdateShareSettingsRequest
from fileflash.services.share import ShareService


class DummySession:
    def __init__(self) -> None:
        self.commit = AsyncMock()
        self.flush = AsyncMock()
        self.execute = AsyncMock()
        self.add = AsyncMock()
        self.scalar = AsyncMock()


def make_settings(**overrides: object) -> Settings:
    payload = {
        "FF_DB_URI": "postgresql://root:pwd@localhost:5432/fileflash",
        "JWT_SECRET_KEY": "unit-test-secret-key-1234567890abcd",
    }
    payload.update(overrides)
    return Settings(**payload)


def make_service(session: DummySession, settings: Settings | None = None) -> ShareService:
    storage = SimpleNamespace(
        iter_object=AsyncMock(),
        iter_object_range=AsyncMock(),
        object_exists=AsyncMock(return_value=False),
        stat_object=AsyncMock(),
    )
    return ShareService(db=session, settings=settings or make_settings(), storage=storage)


def test_share_access_token_roundtrip():
    settings = make_settings()
    token = create_share_access_token(share_id=123, settings=settings, ttl_seconds=60)
    payload = decode_share_access_token(token, settings)
    assert payload["typ"] == "share"
    assert payload["sub"] == "123"


@pytest.mark.asyncio
async def test_create_share_is_idempotent_when_existing_share_found(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = make_service(session)

    existing_share = Share(
        share_id=77,
        user_id=1,
        resource_type="file",
        file_id=1,
        folder_id=None,
        share_link="ABC123",
        share_code="ABC123",
    )

    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=SimpleNamespace(file_id=1)))
    monkeypatch.setattr(service, "_find_existing_active_share", AsyncMock(return_value=existing_share))
    monkeypatch.setattr(service, "_generate_share_code", AsyncMock(side_effect=AssertionError("should not generate code")))
    monkeypatch.setattr(service, "_build_share_schema", AsyncMock(return_value={"id": "existing"}))

    result = await service.create_share(
        user_id=1,
        payload=CreateShareRequest(resourceType="file", resourceId="1"),
    )

    assert result == {"id": "existing"}
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_settings_generates_password_when_enabled(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = make_service(session)

    share_row = Share(
        share_id=1,
        user_id=1,
        resource_type="file",
        file_id=1,
        folder_id=None,
        share_link="ABC123",
        share_code="ABC123",
        password_hash=None,
    )

    monkeypatch.setattr(service, "_get_share_for_update", AsyncMock(return_value=share_row))

    captured: dict[str, str | None] = {"password": None}

    async def _fake_build(_share: Share, *, password: str | None = None):
        captured["password"] = password
        return {"password": password}

    monkeypatch.setattr(service, "_build_share_schema", _fake_build)

    result = await service.update_settings(
        user_id=1,
        share_link="ABC123",
        payload=UpdateShareSettingsRequest(passwordProtected=True),
    )

    assert isinstance(result, dict)
    assert share_row.password_hash is not None
    assert captured["password"] is not None
    assert re.fullmatch(r"\d{6}", captured["password"] or "")
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_settings_accepts_custom_password(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = make_service(session)

    share_row = Share(
        share_id=1,
        user_id=1,
        resource_type="file",
        file_id=1,
        folder_id=None,
        share_link="ABC123",
        share_code="ABC123",
        password_hash=None,
    )

    monkeypatch.setattr(service, "_get_share_for_update", AsyncMock(return_value=share_row))

    captured: dict[str, str | None] = {"password": None}

    async def _fake_build(_share: Share, *, password: str | None = None):
        captured["password"] = password
        return {"password": password}

    monkeypatch.setattr(service, "_build_share_schema", _fake_build)

    result = await service.update_settings(
        user_id=1,
        share_link="ABC123",
        payload=UpdateShareSettingsRequest(passwordProtected=True, password="abcd1234"),
    )

    assert result == {"password": "abcd1234"}
    assert share_row.password_hash is not None
    assert captured["password"] == "abcd1234"


@pytest.mark.asyncio
async def test_save_requires_valid_share_token(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = make_service(session)

    monkeypatch.setattr(service, "_resolve_share_for_access_token", AsyncMock(side_effect=Exception("bad token")))

    with pytest.raises(Exception):
        await service.save_to_my_space(
            user_id=1,
            share_link="ABC123",
            payload=SaveShareRequest(targetFolderId="root", shareAccessToken="bad-token"),
            ip_address="127.0.0.1",
            user_agent="pytest",
        )


@pytest.mark.asyncio
async def test_get_shared_file_stream_prefers_transcoded_when_preview(monkeypatch: pytest.MonkeyPatch):
    session = DummySession()
    service = make_service(session)

    share_row = Share(
        share_id=1,
        user_id=1,
        resource_type="file",
        file_id=9,
        folder_id=None,
        share_link="ABCD",
        share_code="ABCD",
        status="active",
        allow_preview=True,
        allow_download=True,
    )
    file_row = File(
        file_id=9,
        uploader_id=1,
        owner_id=1,
        folder_id=1,
        file_name="video.mp4",
        storage_object_id=33,
        file_size=100,
        file_ext="mp4",
        mime_type="video/mp4",
    )
    source_object = StorageObject(
        object_id=33,
        bucket_name="fileflash",
        object_key="objects/u1/source-video",
        object_size=100,
        upload_status=UploadStatus.ACTIVE,
        content_type="video/mp4",
    )
    optimized_object = StorageObject(
        object_id=34,
        bucket_name="fileflash",
        object_key="optimized/transcode/v1/object-33/source-mp4-v1.mp4",
        object_size=80,
        upload_status=UploadStatus.ACTIVE,
        content_type="video/mp4",
    )
    metadata = FileMediaMetadata(source_object_id=33)
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

    monkeypatch.setattr(service, "_resolve_share_for_access_token", AsyncMock(return_value=share_row))
    monkeypatch.setattr(service, "_get_active_file", AsyncMock(return_value=file_row))
    monkeypatch.setattr(service, "_log_share_event", AsyncMock())
    session.get = AsyncMock(return_value=source_object)
    session.scalar = AsyncMock(side_effect=[metadata, optimized_object])
    session.execute = AsyncMock(return_value=None)
    async def _dummy_stream() -> AsyncIterator[bytes]:
        yield b"data"

    def _iter_object(**_kwargs: object) -> AsyncIterator[bytes]:
        return _dummy_stream()

    iter_mock = Mock(side_effect=_iter_object)
    service.storage.iter_object = iter_mock

    await service.get_shared_file_download_stream_response(
        share_link="ABCD",
        share_access_token="token",
        action="preview",
        range_header=None,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    iter_mock.assert_called_once()
    assert iter_mock.call_args.kwargs["object_key"] == optimized_object.object_key

