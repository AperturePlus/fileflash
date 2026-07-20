from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.errors import ApiError
from fileflash.core.settings import Settings
from fileflash.schemas.auth import RegisterRequest
from fileflash.schemas.user import User, UserPreference
from fileflash.services.auth import AuthService


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.commit = AsyncMock()
        self.flush = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.get = AsyncMock()
        self.refresh = AsyncMock()


def make_settings(**overrides: object) -> Settings:
    payload = {
        "FF_DB_URI": "postgresql://root:pwd@localhost:5432/fileflash",
        "JWT_SECRET_KEY": "unit-test-secret-key-1234567890abcd",
    }
    payload.update(overrides)
    return Settings(**payload)


def make_service(session: DummySession) -> AuthService:
    event_publisher = SimpleNamespace(publish=AsyncMock())
    rate_limiter = SimpleNamespace(allow=AsyncMock(return_value=True))
    verification_email_delivery = SimpleNamespace(send_verification_email=AsyncMock())
    return AuthService(
        db=session,  # type: ignore[arg-type]
        settings=make_settings(),
        rate_limiter=rate_limiter,
        event_publisher=event_publisher,
        verification_email_delivery=verification_email_delivery,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_register_rejects_when_no_enabled_rules() -> None:
    session = DummySession()
    service = make_service(session)
    session.scalar = AsyncMock(return_value=None)
    session.scalars = AsyncMock(return_value=[])

    with pytest.raises(ApiError, match="邮箱后缀不被允许，请更换邮箱"):
        await service.register(
            RegisterRequest(username="new", email="new@example.com", password="123456"),
            client_ip="127.0.0.1",
            user_agent="pytest",
        )


@pytest.mark.asyncio
async def test_register_accepts_matching_rule() -> None:
    session = DummySession()
    service = make_service(session)
    session.scalar = AsyncMock(return_value=None)
    session.scalars = AsyncMock(
        return_value=[SimpleNamespace(pattern=r".*\.example\.com", enabled=True)]
    )
    service._to_user_schema = Mock(
        return_value=User(
            user_id="1",
            username="new",
            email="new@dept.example.com",
            storage_limit=1024,
            storage_used=0,
            created_at=datetime.now(UTC),
            role="user",
            status="active",
            email_verified=False,
            email_verified_at=None,
            preference=UserPreference(language="zh-CN"),
        )
    )  # type: ignore[method-assign]
    service._create_email_verification_token = AsyncMock(return_value="verify-token")  # type: ignore[method-assign]

    result = await service.register(
        RegisterRequest(username="new", email="new@dept.example.com", password="123456"),
        client_ip="127.0.0.1",
        user_agent="pytest",
    )

    assert result.email_verification_required is True
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_rejects_non_matching_rule() -> None:
    session = DummySession()
    service = make_service(session)
    session.scalar = AsyncMock(return_value=None)
    session.scalars = AsyncMock(
        return_value=[SimpleNamespace(pattern=r".*\.corp\.com", enabled=True)]
    )

    with pytest.raises(ApiError, match="邮箱后缀不被允许，请更换邮箱"):
        await service.register(
            RegisterRequest(username="new", email="new@example.com", password="123456"),
            client_ip="127.0.0.1",
            user_agent="pytest",
        )
