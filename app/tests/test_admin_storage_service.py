from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.errors import ApiError
from fileflash.models.enums import UserRole, UserStatus
from fileflash.models.tables_identity import User
from fileflash.schemas.admin.storage import UsageTrendQuery
from fileflash.services.admin.storage import AdminStorageService


def _user(**kwargs) -> User:
    base = dict(
        user_id=1,
        username="bob",
        email="b@x.com",
        password_hash="x",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        email_verified_at=datetime.now(UTC),
        storage_limit=10 * 1024 * 1024 * 1024,
        storage_used=2 * 1024 * 1024 * 1024,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    base.update(kwargs)
    return User(**base)


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.get = AsyncMock()
        self.execute = AsyncMock()


@pytest.mark.asyncio
async def test_summary_aggregates_users_and_files() -> None:
    session = DummySession()
    session.scalar.side_effect = [
        2 * 1024 * 1024 * 1024,
        10 * 1024 * 1024 * 1024,
        42,
        7,
    ]
    service = AdminStorageService(db=session, redis=None)  # type: ignore[arg-type]

    result = await service.summary()

    assert result.storage_used == 2 * 1024 * 1024 * 1024
    assert result.user_count == 7
    assert result.file_count == 42
    assert round(result.storage_percentage, 2) == 20.0


@pytest.mark.asyncio
async def test_update_quota_rejects_below_usage() -> None:
    session = DummySession()
    target = _user(storage_used=5 * 1024 * 1024 * 1024)
    session.get.return_value = target
    service = AdminStorageService(db=session, redis=None)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as exc:
        await service.update_quota(user_id=1, new_limit=1 * 1024 * 1024 * 1024)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_update_quota_success_updates_and_commits() -> None:
    session = DummySession()
    target = _user(storage_used=1 * 1024 * 1024 * 1024)
    session.get.return_value = target
    service = AdminStorageService(db=session, redis=None)  # type: ignore[arg-type]

    result = await service.update_quota(user_id=1, new_limit=20 * 1024 * 1024 * 1024)

    assert result.storage_limit == 20 * 1024 * 1024 * 1024
    assert target.storage_limit == 20 * 1024 * 1024 * 1024
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_usage_trend_returns_n_points() -> None:
    session = DummySession()
    session.scalar.return_value = 2 * 1024 * 1024 * 1024
    session.execute.return_value = Mock(all=lambda: [])
    service = AdminStorageService(db=session, redis=None)  # type: ignore[arg-type]

    result = await service.usage_trend(query=UsageTrendQuery(days=7))

    assert len(result.trends) == 7
    assert result.is_estimated is True
