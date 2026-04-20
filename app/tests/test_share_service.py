from __future__ import annotations

import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.core.security import create_share_access_token, decode_share_access_token
from src.core.settings import Settings
from src.models.tables_access_share import Share
from src.schemas.share import CreateShareRequest, SaveShareRequest, UpdateShareSettingsRequest
from src.services.share import ShareService


class DummySession:
    def __init__(self) -> None:
        self.commit = AsyncMock()
        self.flush = AsyncMock()
        self.execute = AsyncMock()
        self.add = AsyncMock()


def make_settings(**overrides: object) -> Settings:
    payload = {
        "FF_DB_URI": "postgresql://root:pwd@localhost:5432/fileflash",
        "JWT_SECRET_KEY": "unit-test-secret-key-1234567890abcd",
    }
    payload.update(overrides)
    return Settings(**payload)


def make_service(session: DummySession, settings: Settings | None = None) -> ShareService:
    storage = SimpleNamespace(iter_object=AsyncMock())
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

