from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.errors import ApiError
from fileflash.models.enums import FileStatus, ScanResult
from fileflash.schemas.admin.files import AdminFileAuditOwner, ListAdminFilesQuery
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


@pytest.mark.asyncio
async def test_detail_aggregates_active_object_owner_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    session = DummySession()
    service = AdminFilesService(db=session, publisher=DummyPublisher())  # type: ignore[arg-type]
    now = datetime.now(UTC)
    file_row = Mock(
        file_id=10,
        file_name="report.pdf",
        file_size=128,
        mime_type="application/pdf",
        file_ext="pdf",
        updated_at=now,
        created_at=now,
    )
    object_row = Mock(
        object_id=20,
        object_hash="a" * 64,
        hash_algorithm="sha256",
        content_type="application/pdf",
        upload_status="active",
    )
    owner_row = Mock(username="alice")
    scan_row = Mock(
        result=ScanResult.CLEAN,
        scan_type="virus",
        scanned_at=now,
        details={"engine": "unit"},
    )
    owners = [
        AdminFileAuditOwner(
            user_id="1",
            username="alice",
            email="alice@example.com",
            file_count=2,
            first_uploaded_at=now,
            last_uploaded_at=now,
        ),
        AdminFileAuditOwner(
            user_id="2",
            username="bob",
            email="bob@example.com",
            file_count=1,
            first_uploaded_at=now,
            last_uploaded_at=now,
        ),
    ]

    monkeypatch.setattr(
        service,
        "_get_active_file_context",
        AsyncMock(return_value=(file_row, object_row, owner_row, scan_row)),
    )
    monkeypatch.setattr(service, "_load_object_owners", AsyncMock(return_value=owners))
    monkeypatch.setattr(service, "_object_is_shared", AsyncMock(return_value=True))

    detail = await service.get_file_detail(file_id=10)

    assert detail.object_id == "20"
    assert detail.upload_count == 3
    assert detail.owner_count == 2
    assert detail.is_shared is True
    assert detail.latest_scan and detail.latest_scan.virus_status == "clean"
