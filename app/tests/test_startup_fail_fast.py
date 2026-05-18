from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from fileflash.main import lifespan
from fileflash.s3.minio_client import ObjectStorageAuthError


@pytest.mark.asyncio
async def test_lifespan_fails_fast_when_database_check_fails(monkeypatch: pytest.MonkeyPatch):
    verify = AsyncMock(side_effect=RuntimeError("database unavailable"))
    verify_schema = AsyncMock()
    seed = AsyncMock()
    monkeypatch.setattr("fileflash.main.verify_database_connection", verify)
    monkeypatch.setattr("fileflash.main.verify_schema_compatibility", verify_schema)
    monkeypatch.setattr("fileflash.main.initialize_dev_accounts", seed)

    with pytest.raises(RuntimeError, match="database unavailable"):
        async with lifespan(object()):
            pass

    verify.assert_awaited_once()
    verify_schema.assert_not_awaited()
    seed.assert_not_awaited()


@pytest.mark.asyncio
async def test_lifespan_fails_fast_when_schema_check_fails(monkeypatch: pytest.MonkeyPatch):
    verify = AsyncMock()
    verify_schema = AsyncMock(side_effect=RuntimeError("schema incompatible"))
    seed = AsyncMock()
    monkeypatch.setattr("fileflash.main.verify_database_connection", verify)
    monkeypatch.setattr("fileflash.main.verify_schema_compatibility", verify_schema)
    monkeypatch.setattr("fileflash.main.initialize_dev_accounts", seed)

    with pytest.raises(RuntimeError, match="schema incompatible"):
        async with lifespan(object()):
            pass

    verify.assert_awaited_once()
    verify_schema.assert_awaited_once()
    seed.assert_not_awaited()


@pytest.mark.asyncio
async def test_lifespan_fails_fast_when_object_storage_check_fails(monkeypatch: pytest.MonkeyPatch):
    verify = AsyncMock()
    verify_schema = AsyncMock()
    seed = AsyncMock()
    storage = SimpleNamespace(ensure_bucket=AsyncMock(side_effect=ObjectStorageAuthError("bad credentials")))
    monkeypatch.setattr("fileflash.main.verify_database_connection", verify)
    monkeypatch.setattr("fileflash.main.verify_schema_compatibility", verify_schema)
    monkeypatch.setattr("fileflash.main.get_object_storage", lambda: storage)
    monkeypatch.setattr("fileflash.main.initialize_dev_accounts", seed)

    with pytest.raises(ObjectStorageAuthError, match="bad credentials"):
        async with lifespan(object()):
            pass

    verify.assert_awaited_once()
    verify_schema.assert_awaited_once()
    storage.ensure_bucket.assert_awaited_once()
    seed.assert_not_awaited()
