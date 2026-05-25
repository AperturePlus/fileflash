from __future__ import annotations

import pytest

from fileflash.core.settings import Settings
from fileflash.services.admin.system import AdminSystemService


class DummySession:
    async def scalar(self, _query: object) -> int:
        return 0


def make_settings(**overrides: object) -> Settings:
    payload = {
        "FF_DB_URI": "postgresql://root:pwd@localhost:5432/fileflash",
        "JWT_SECRET_KEY": "unit-test-secret-key-1234567890abcd",
    }
    payload.update(overrides)
    return Settings(**payload)


@pytest.mark.asyncio
async def test_health_hash_computation_enabled_follows_settings() -> None:
    disabled_service = AdminSystemService(
        db=DummySession(),
        settings=make_settings(UPLOAD_VERIFY_MERGED_OBJECT_HASH=False),
    )
    disabled_health = await disabled_service.health()
    assert disabled_health.hash_computation_enabled is False

    enabled_service = AdminSystemService(
        db=DummySession(),
        settings=make_settings(UPLOAD_VERIFY_MERGED_OBJECT_HASH=True),
    )
    enabled_health = await enabled_service.health()
    assert enabled_health.hash_computation_enabled is True
