from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.errors import ApiError
from fileflash.schemas.admin.moderation import ListViolationsQuery
from fileflash.services.admin.moderation import AdminModerationService


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.commit = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.get = AsyncMock()
        self.execute = AsyncMock()


@pytest.mark.asyncio
async def test_resolve_missing_case_returns_404() -> None:
    session = DummySession()
    session.get.return_value = None
    service = AdminModerationService(db=session)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as exc:
        await service.resolve_case(case_id=1, handled_by=2)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_resolve_already_resolved_returns_409() -> None:
    session = DummySession()
    case = Mock(case_id=1, status="resolved")
    session.get.return_value = case
    service = AdminModerationService(db=session)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as exc:
        await service.resolve_case(case_id=1, handled_by=2)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_resolve_pending_case_sets_resolved() -> None:
    session = DummySession()
    case = Mock(case_id=1, status="pending", handled_by=None, handled_at=None, resolution=None, file_id=10)
    session.get.return_value = case
    service = AdminModerationService(db=session)  # type: ignore[arg-type]

    result = await service.resolve_case(case_id=1, handled_by=2)

    assert result.violation_id == "1"
    assert case.status == "resolved"
    assert case.resolution == "admin_clear"
    assert case.handled_by == 2
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_list_returns_empty_paginated() -> None:
    session = DummySession()
    session.scalar.return_value = 0
    session.execute.return_value = Mock(all=lambda: [])
    service = AdminModerationService(db=session)  # type: ignore[arg-type]

    result = await service.list_violations(query=ListViolationsQuery())
    assert result.items == []
    assert result.pagination.total_items == 0
