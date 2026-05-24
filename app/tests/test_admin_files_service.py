from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.errors import ApiError
from fileflash.models.enums import FileStatus
from fileflash.schemas.admin.files import ListAdminFilesQuery
from fileflash.services.admin.files import AdminFilesService


class DummyPublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, payload: dict) -> None:  # noqa: ANN001
        self.calls.append((event_name, payload))


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.commit = AsyncMock()
        self.execute = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.get = AsyncMock()


@pytest.mark.asyncio
async def test_list_returns_paginated_empty_when_no_files() -> None:
    session = DummySession()
    session.scalar.return_value = 0
    session.execute.return_value = Mock(all=lambda: [])
    service = AdminFilesService(db=session, publisher=DummyPublisher())  # type: ignore[arg-type]

    result = await service.list_files(query=ListAdminFilesQuery())

    assert result.items == []
    assert result.pagination.total_items == 0


@pytest.mark.asyncio
async def test_rescan_missing_file_returns_404() -> None:
    session = DummySession()
    session.get.return_value = None
    service = AdminFilesService(db=session, publisher=DummyPublisher())  # type: ignore[arg-type]

    with pytest.raises(ApiError) as exc:
        await service.request_rescan(file_id=1, requested_by=99)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_rescan_inserts_scan_record_and_publishes_event() -> None:
    session = DummySession()
    file_row = Mock(
        file_id=1,
        storage_object_id=2,
        deleted_at=None,
        status=FileStatus.ACTIVE,
    )
    session.get.return_value = file_row
    publisher = DummyPublisher()
    service = AdminFilesService(db=session, publisher=publisher)  # type: ignore[arg-type]

    result = await service.request_rescan(file_id=1, requested_by=99)

    assert result.virus_status == "pending"
    assert publisher.calls and publisher.calls[0][0] == "files.rescan_requested"
    session.commit.assert_awaited()
