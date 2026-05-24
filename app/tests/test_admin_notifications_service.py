from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from fileflash.core.errors import ApiError
from fileflash.schemas.admin.notifications import BroadcastRequest
from fileflash.services.admin.notifications import (
    MAX_BROADCAST_RECIPIENTS,
    AdminNotificationsService,
)


class DummySession:
    def __init__(self) -> None:
        self.add = Mock()
        self.add_all = Mock()
        self.commit = AsyncMock()
        self.scalar = AsyncMock()
        self.scalars = AsyncMock()
        self.execute = AsyncMock()


@pytest.mark.asyncio
async def test_broadcast_rejects_empty_message() -> None:
    session = DummySession()
    service = AdminNotificationsService(db=session)  # type: ignore[arg-type]
    with pytest.raises(ApiError):
        await service.broadcast(
            payload=BroadcastRequest.model_construct(title=None, message="", type="system"),
            sender_id=1,
        )


@pytest.mark.asyncio
async def test_broadcast_too_many_recipients_returns_422() -> None:
    session = DummySession()
    session.scalar.return_value = MAX_BROADCAST_RECIPIENTS + 1
    service = AdminNotificationsService(db=session)  # type: ignore[arg-type]
    with pytest.raises(ApiError) as exc:
        await service.broadcast(payload=BroadcastRequest(message="hi", type="system"), sender_id=1)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_broadcast_writes_one_row_per_recipient() -> None:
    session = DummySession()
    session.scalar.return_value = 3
    session.scalars.return_value = iter([10, 11, 12])
    service = AdminNotificationsService(db=session)  # type: ignore[arg-type]

    result = await service.broadcast(payload=BroadcastRequest(message="ping", type="system"), sender_id=1)

    assert result.recipient_count == 3
    assert session.add_all.called
