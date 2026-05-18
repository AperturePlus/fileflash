from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.security import get_password_hash, hash_token
from fileflash.core.settings import Settings
from fileflash.models.enums import UiLanguage, UserRole, UserStatus
from fileflash.models.tables_audit_security import Log
from fileflash.models.tables_identity import User, UserPreference, UserSession
from fileflash.schemas.user import ChangePasswordRequest, GetActivityLogQuery, UpdateProfileRequest
from fileflash.services.auth import AuthService


class DummyResult:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[object, ...]]:
        return self._rows


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.commit = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.get = AsyncMock()
        self.execute = AsyncMock()


def make_settings(**overrides: object) -> Settings:
    payload = {
        "FF_DB_URI": "postgresql://root:pwd@localhost:5432/fileflash",
        "JWT_SECRET_KEY": "unit-test-secret-key-1234567890abcd",
    }
    payload.update(overrides)
    return Settings(**payload)


def make_service(session: DummySession, publisher: AsyncMock | None = None) -> AuthService:
    event_publisher = SimpleNamespace(publish=publisher or AsyncMock())
    rate_limiter = SimpleNamespace(allow=AsyncMock(return_value=True))
    return AuthService(
        db=session,
        settings=make_settings(),
        rate_limiter=rate_limiter,
        event_publisher=event_publisher,
    )


@pytest.mark.asyncio
async def test_update_profile_resets_email_verification_and_publishes_event():
    session = DummySession()
    publish_mock = AsyncMock()
    service = make_service(session, publisher=publish_mock)

    user = User(
        user_id=1,
        username="demo",
        email="demo@old.local",
        password_hash="hash",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        storage_limit=1024,
        storage_used=128,
        email_verified=True,
        email_verified_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    preference = UserPreference(user_id=1, ui_language=UiLanguage.ZH_CN)
    session.scalar = AsyncMock(side_effect=[user, None, None])

    service._get_user_preference = AsyncMock(return_value=preference)  # type: ignore[method-assign]
    service._create_email_verification_token = AsyncMock(return_value="verify-token")  # type: ignore[method-assign]

    profile = await service.update_profile(
        user_id=1,
        payload=UpdateProfileRequest(username="demo-next", email="demo@new.local"),
        user_agent="pytest-agent",
    )

    assert profile.username == "demo-next"
    assert profile.email == "demo@new.local"
    assert user.email_verified is False
    assert user.email_verified_at is None
    session.commit.assert_awaited_once()
    publish_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_password_revokes_other_sessions_only():
    session = DummySession()
    service = make_service(session)

    user = User(
        user_id=2,
        username="alice",
        email="alice@example.com",
        password_hash=get_password_hash("old-password"),
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        storage_limit=1024,
        storage_used=64,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    keep_refresh_token = "keep-token"
    keep_session = UserSession(
        session_id=11,
        user_id=2,
        refresh_token_hash=hash_token(keep_refresh_token),
        client_type="web",
        expire_at=datetime.now(UTC),
    )
    other_session = UserSession(
        session_id=12,
        user_id=2,
        refresh_token_hash=hash_token("other-token"),
        client_type="web",
        expire_at=datetime.now(UTC),
    )
    session.scalar = AsyncMock(return_value=user)
    session.scalars = AsyncMock(return_value=[keep_session, other_session])

    await service.change_password(
        user_id=2,
        payload=ChangePasswordRequest(oldPassword="old-password", newPassword="new-password"),
        current_refresh_token=keep_refresh_token,
    )

    assert keep_session.revoked_at is None
    assert other_session.revoked_at is not None
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_activity_log_builds_paginated_items():
    session = DummySession()
    service = make_service(session)
    now = datetime.now(UTC)

    log1 = Log(
        id=101,
        user_id=1,
        operation="file_upload",
        metadata_payload={"fileName": "demo.txt"},
        details="uploaded",
        ip_address="127.0.0.1",
        user_agent="UA-1",
        performed_at=now,
    )
    log2 = Log(
        id=102,
        user_id=1,
        operation="login",
        metadata_payload={},
        details="login ok",
        ip_address="127.0.0.2",
        user_agent="UA-2",
        performed_at=now,
    )

    session.scalar = AsyncMock(return_value=2)
    session.scalars = AsyncMock(return_value=[log1, log2])

    result = await service.get_activity_log(
        user_id=1,
        query=GetActivityLogQuery(page=1, perPage=10, operation=None),
    )

    assert result.pagination.total_items == 2
    assert len(result.items) == 2
    assert result.items[0].details["fileName"] == "demo.txt"
    assert result.items[1].details["message"] == "login ok"


@pytest.mark.asyncio
async def test_get_storage_summary_aggregates_files_and_folders():
    session = DummySession()
    service = make_service(session)
    user = User(
        user_id=3,
        username="bob",
        email="bob@example.com",
        password_hash="hash",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        storage_limit=1_000,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.get = AsyncMock(return_value=user)
    session.execute = AsyncMock(
        return_value=DummyResult(
            [
                (100, "image/png", "png"),
                (200, "application/pdf", "pdf"),
                (300, "application/zip", "zip"),
            ]
        )
    )
    session.scalar = AsyncMock(return_value=4)

    summary = await service.get_storage_summary(user_id=3)

    assert summary.storage_used == 600
    assert summary.storage_available == 400
    assert summary.file_count == 3
    assert summary.folder_count == 4
    assert summary.breakdown["images"].count == 1
    assert summary.breakdown["documents"].count == 1
    assert summary.breakdown["archives"].count == 1
