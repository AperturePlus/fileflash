from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.errors import ApiError
from fileflash.models.enums import UserRole, UserStatus
from fileflash.models.tables_identity import User
from fileflash.schemas.admin.users import ListAdminUsersQuery
from fileflash.services.admin.users import AdminUsersService


def _user(**kwargs) -> User:
    base = dict(
        user_id=1,
        username="alice",
        email="alice@example.com",
        password_hash="x",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        email_verified_at=datetime.now(UTC),
        storage_limit=10 * 1024 * 1024 * 1024,
        storage_used=1024,
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
async def test_list_users_returns_paginated_items() -> None:
    session = DummySession()
    session.scalar.return_value = 1
    session.scalars.return_value = [_user()]
    session.execute.return_value = Mock(all=lambda: [])
    service = AdminUsersService(db=session)  # type: ignore[arg-type]

    result = await service.list_users(query=ListAdminUsersQuery())

    assert result.pagination.total_items == 1
    assert result.items[0].username == "alice"
    assert result.items[0].status == "active"


@pytest.mark.asyncio
async def test_set_status_user_not_found() -> None:
    session = DummySession()
    session.get.return_value = None
    service = AdminUsersService(db=session)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as exc:
        await service.set_status(user_id=999, external_status="suspended")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_set_status_suspend_last_admin_blocked() -> None:
    session = DummySession()
    admin = _user(user_id=2, role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    session.get.return_value = admin
    session.scalar.return_value = 0
    service = AdminUsersService(db=session)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as exc:
        await service.set_status(user_id=2, external_status="suspended")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_set_status_suspends_user_and_revokes_sessions() -> None:
    session = DummySession()
    target = _user(user_id=3)
    session.get.return_value = target
    session.scalar.return_value = 5
    service = AdminUsersService(db=session)  # type: ignore[arg-type]

    result = await service.set_status(user_id=3, external_status="suspended")

    assert result.status == "suspended"
    assert target.status == UserStatus.DISABLED
    session.commit.assert_awaited()
