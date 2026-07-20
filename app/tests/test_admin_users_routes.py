from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fileflash.core.deps import get_admin_users_service, require_admin
from fileflash.core.errors import ApiError, api_error_handler
from fileflash.routers.admin_users import router as admin_users_router
from fileflash.schemas.admin.users import (
    AdminUserItem,
    AdminUserUsageStats,
    UpdateUserStatusResponse,
)
from fileflash.schemas.common import PaginatedData, PaginationMeta


class StubService:
    async def list_users(self, *, query):  # noqa: ANN001
        item = AdminUserItem(
            user_id="1",
            username="alice",
            email="a@x.com",
            role="USER",
            status="active",
            email_verified=True,
            email_verified_at=None,
            storage_limit=1024,
            storage_used=0,
            usage_percentage=0.0,
            last_login_at=None,
            last_active_at=None,
            created_at=datetime.now(UTC),
            usage_stats=AdminUserUsageStats(traffic_bytes=1024, agent_tokens=42),
        )
        return PaginatedData(
            items=[item],
            pagination=PaginationMeta(
                total_items=1,
                total_pages=1,
                per_page=query.per_page,
                current_page=query.page,
                has_prev=False,
                has_next=False,
            ),
        )

    async def set_status(self, *, user_id, external_status):  # noqa: ANN001
        return UpdateUserStatusResponse(
            user_id=str(user_id),
            status=external_status,
            updated_at=datetime.now(UTC),
        )


def _client(admin: bool) -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(admin_users_router, prefix="/api/v1")
    app.dependency_overrides[get_admin_users_service] = lambda: StubService()
    if admin:
        app.dependency_overrides[require_admin] = lambda: SimpleNamespace(user_id=1)
    else:

        async def _deny():
            raise ApiError(status_code=403, code=403, message="forbidden")

        app.dependency_overrides[require_admin] = _deny
    return TestClient(app)


def test_admin_can_list_users() -> None:
    with _client(admin=True) as c:
        resp = c.get("/api/v1/admin/users")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["items"][0]["username"] == "alice"
    assert body["data"]["items"][0]["usageStats"] == {"trafficBytes": 1024, "agentTokens": 42}


def test_non_admin_gets_403() -> None:
    with _client(admin=False) as c:
        resp = c.get("/api/v1/admin/users")
    assert resp.status_code == 403


def test_usage_window_requires_both_bounds() -> None:
    with _client(admin=True) as c:
        resp = c.get("/api/v1/admin/users?usageFrom=2026-01-01T00:00:00Z")
    assert resp.status_code == 400


def test_usage_window_rejects_reversed_bounds() -> None:
    with _client(admin=True) as c:
        resp = c.get(
            "/api/v1/admin/users"
            "?usageFrom=2026-02-01T00:00:00Z"
            "&usageTo=2026-01-01T00:00:00Z"
        )
    assert resp.status_code == 400


def test_usage_window_rejects_more_than_90_days() -> None:
    with _client(admin=True) as c:
        resp = c.get(
            "/api/v1/admin/users"
            "?usageFrom=2026-01-01T00:00:00Z"
            "&usageTo=2026-04-02T00:00:00Z"
        )
    assert resp.status_code == 400


def test_admin_can_patch_status() -> None:
    with _client(admin=True) as c:
        resp = c.patch("/api/v1/admin/users/42/status", json={"status": "suspended"})
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "suspended"
