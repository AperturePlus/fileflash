from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.main import lifespan
from src.s3.minio_client import ObjectStorageAuthError


@pytest.mark.asyncio
async def test_lifespan_fails_fast_when_database_check_fails(monkeypatch: pytest.MonkeyPatch):
    verify = AsyncMock(side_effect=RuntimeError("database unavailable"))
    seed = AsyncMock()
    monkeypatch.setattr("src.main.verify_database_connection", verify)
    monkeypatch.setattr("src.main.initialize_dev_accounts", seed)

    with pytest.raises(RuntimeError, match="database unavailable"):
        async with lifespan(object()):
            pass

    verify.assert_awaited_once()
    seed.assert_not_awaited()


@pytest.mark.asyncio
async def test_lifespan_fails_fast_when_object_storage_check_fails(monkeypatch: pytest.MonkeyPatch):
    verify = AsyncMock()
    seed = AsyncMock()
    storage = SimpleNamespace(ensure_bucket=AsyncMock(side_effect=ObjectStorageAuthError("bad credentials")))
    monkeypatch.setattr("src.main.verify_database_connection", verify)
    monkeypatch.setattr("src.main.get_object_storage", lambda: storage)
    monkeypatch.setattr("src.main.initialize_dev_accounts", seed)

    with pytest.raises(ObjectStorageAuthError, match="bad credentials"):
        async with lifespan(object()):
            pass

    verify.assert_awaited_once()
    storage.ensure_bucket.assert_awaited_once()
    seed.assert_not_awaited()
