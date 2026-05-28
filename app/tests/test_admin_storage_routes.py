from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import get_admin_storage_service, require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_storage import router as storage_router
from fileflash.schemas.admin.storage import (
    AdminStorageSummary,
    UpdateQuotaResponse,
    UsageTrendPoint,
    UsageTrendResponse,
)


class StubService:
    async def summary(self):  # noqa: ANN201
        return AdminStorageSummary(
            storage_used=1000,
            storage_limit=10000,
            storage_percentage=10.0,
            file_count=3,
            user_count=2,
            updated_at=datetime.now(UTC),
        )

    async def list_storage_users(self, *, query):  # noqa: ANN001, ANN201
        return SimpleNamespace(
            model_dump=lambda **_: {
                "items": [],
                "pagination": {
                    "totalItems": 0,
                    "totalPages": 1,
                    "perPage": query.per_page,
                    "currentPage": query.page,
                    "hasPrev": False,
                    "hasNext": False,
                },
            }
        )

    async def update_quota(self, *, user_id, new_limit):  # noqa: ANN001, ANN201
        return UpdateQuotaResponse(
            user_id=str(user_id),
            storage_limit=new_limit,
            storage_used=0,
            usage_percentage=0.0,
            updated_at=datetime.now(UTC),
        )

    async def usage_trend(self, *, query):  # noqa: ANN001, ANN201
        _ = query
        return UsageTrendResponse(
            trends=[UsageTrendPoint(date="2026-05-24", used=1)],
            is_estimated=False,
        )


def _client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(storage_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_storage_service] = lambda: StubService()
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=1)
    return TestClient(app)


def test_summary_returns_camel_case() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/storage/summary")
    assert resp.status_code == 200
    assert "storageUsed" in resp.json()["data"]


def test_update_quota_passes_storage_limit() -> None:
    with _client() as c:
        resp = c.patch("/api/v1/admin/storage/users/7/quota", json={"storageLimit": 1024})
    assert resp.status_code == 200
    assert resp.json()["data"]["storageLimit"] == 1024


def test_usage_trend_default_days() -> None:
    with _client() as c:
        resp = c.get("/api/v1/admin/storage/usage-trend")
    assert resp.status_code == 200
    assert len(resp.json()["data"]["trends"]) == 1
