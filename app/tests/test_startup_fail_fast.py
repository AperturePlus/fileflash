from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from fileflash.core.settings import Settings
from fileflash.main import lifespan
from fileflash.s3.minio_client import ObjectStorageAuthError


def make_settings(**overrides: object) -> Settings:
    payload = {
        "FF_DB_URI": "postgresql://root:pwd@localhost:5432/fileflash",
        "APP_ENV": "production",
        "JWT_SECRET_KEY": "unit-test-secret-key-1234567890abcd",
        "DEFAULT_ADMIN_USERNAME": "admin",
        "DEFAULT_ADMIN_EMAIL": "admin@example.com",
        "DEFAULT_ADMIN_PASSWORD": "p" * 32,
    }
    payload.update(overrides)
    return Settings(_env_file=None, **payload)


@pytest.mark.asyncio
async def test_lifespan_fails_fast_when_database_check_fails(monkeypatch: pytest.MonkeyPatch):
    verify = AsyncMock(side_effect=RuntimeError("database unavailable"))
    verify_schema = AsyncMock()
    seed = AsyncMock()
    monkeypatch.setattr("fileflash.main.settings", make_settings())
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
    monkeypatch.setattr("fileflash.main.settings", make_settings())
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
    storage = SimpleNamespace(
        ensure_bucket=AsyncMock(side_effect=ObjectStorageAuthError("bad credentials"))
    )
    monkeypatch.setattr("fileflash.main.settings", make_settings())
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


@pytest.mark.asyncio
async def test_lifespan_fails_fast_when_prod_admin_env_missing(monkeypatch: pytest.MonkeyPatch):
    verify = AsyncMock()
    verify_schema = AsyncMock()
    seed = AsyncMock()
    monkeypatch.setattr(
        "fileflash.main.settings",
        Settings(
            _env_file=None,
            FF_DB_URI="postgresql://root:pwd@localhost:5432/fileflash",
            APP_ENV="production",
            JWT_SECRET_KEY="unit-test-secret-key-1234567890abcd",
        ),
    )
    monkeypatch.setattr("fileflash.main.verify_database_connection", verify)
    monkeypatch.setattr("fileflash.main.verify_schema_compatibility", verify_schema)
    monkeypatch.setattr("fileflash.main.initialize_dev_accounts", seed)

    with pytest.raises(ValueError, match="DEFAULT_ADMIN_USERNAME is required in production"):
        async with lifespan(object()):
            pass

    verify.assert_not_awaited()
    verify_schema.assert_not_awaited()
    seed.assert_not_awaited()


@pytest.mark.asyncio
async def test_lifespan_fails_fast_when_prod_admin_password_too_short(
    monkeypatch: pytest.MonkeyPatch,
):
    verify = AsyncMock()
    verify_schema = AsyncMock()
    seed = AsyncMock()
    monkeypatch.setattr(
        "fileflash.main.settings",
        make_settings(DEFAULT_ADMIN_PASSWORD="short-password"),
    )
    monkeypatch.setattr("fileflash.main.verify_database_connection", verify)
    monkeypatch.setattr("fileflash.main.verify_schema_compatibility", verify_schema)
    monkeypatch.setattr("fileflash.main.initialize_dev_accounts", seed)

    with pytest.raises(ValueError, match="DEFAULT_ADMIN_PASSWORD must be at least 32 bytes"):
        async with lifespan(object()):
            pass

    verify.assert_not_awaited()
    verify_schema.assert_not_awaited()
    seed.assert_not_awaited()
